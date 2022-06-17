"""Client connection entry point.

Listen for connection on a public port and dispatch
them to connection handlers/callbacks.
"""

import asyncio
import logging
import ssl

import websockets.server as ws

from common.messages_types import (
    SetUserIdMessage,
    ZKPForPubKeyAccMessage,
    msg_recv,
    msg_send,
)
from .crypto import Crypto
from .session_manager_server import SessionsManager


class ServerAuthFailed(Exception):
    """Error thrown on authentication failure."""

    pass


class ConnectionListener:
    """Listen on a public port and authenticate incoming clients."""

    def __init__(
        self, hostname: str, port: int, certpath: str, keypath: str
    ) -> None:
        """Construct a connection listener instance."""
        self.hostname = hostname
        self.port = port
        self.certpath = certpath
        self.keypath = keypath
        self.session_manager = SessionsManager()
        self.log = logging.getLogger("logger")
        self.log.info("Server connection listener is alive")
        self.logged_users_num = 0

    async def run(self) -> None:
        """Open a public port and listen for connections."""
        self.log.info(f"Hostname is {self.hostname}")

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            certfile=self.certpath,
            keyfile=self.keypath,
        )

        self.log.info(
            f"SSL context established. Opening public port: {self.port}..."
        )

        async with ws.serve(
            ws_handler=self.__handle_connection,
            host=self.hostname,
            port=self.port,
            ssl=ssl_context,
        ):
            await asyncio.Future()

    async def __handle_connection(
        self, conn: ws.WebSocketServerProtocol
    ) -> None:
        """Handle a new incoming connection."""
        self.log.info(
            f"Accepted connection from {conn.remote_address[0]}:"
            f"{conn.remote_address[1]}"
        )

        # log in the User
        try:
            user_login_message = await msg_recv(conn)
            public_key = user_login_message.payload["public_key"]
            self.log.info(
                f"Server received message from Client with {public_key=}."
            )
            user_id = self.logged_users_num
            self.logged_users_num += 1

            set_user_id_message = SetUserIdMessage(user_id=user_id)
            await msg_send(set_user_id_message, conn)
            self.log.info(f"Server sent {user_id=} to Client.")

            zkp_for_pubkey_message = await msg_recv(conn)
            signature = zkp_for_pubkey_message.payload["signature"]
            exponent = zkp_for_pubkey_message.payload["exponent"]
            self.log.info(
                f"Server received {signature=} {exponent=} "
                f"for public key from client {user_id}."
            )

            acceptance = Crypto.verify_schnorr_signature(user_id, signature, exponent, public_key)
            acceptance_message = ZKPForPubKeyAccMessage(acceptance=acceptance)
            await msg_send(acceptance_message, conn)
            self.log.info(
                f"Server sent {acceptance=} for ZKP for public key "
                f"to Client {user_id}."
            )
            self.log.info(f"Successfully logged in Client {user_id}.")
            await self.session_manager.add_session_with_user(
                conn=conn,
                user_id=str(user_id),
                public_key=public_key,
                public_key_proof=(signature, exponent),
            )

        except ServerAuthFailed:
            self.log.error(
                f"User authentication failed: "
                f"{conn.remote_address[0]}:{conn.remote_address[1]}"
            )
            # Terminate the connection with application error code
            await conn.close(code=3000, reason="Authentication failed")
        except Exception:
            self.log.error("Unexpected error occurred!", exc_info=True)
