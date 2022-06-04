"""Client connection entry point.

Listen for connection on a public port and dispatch
them to connection handlers/callbacks.
"""

import asyncio
import logging
import ssl

import websockets.server as ws

from common.messages_types import msg_recv

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
            message = await msg_recv(conn)

            await self.session_manager.login_user_entry(
                conn=conn,
                user_id=user_id,
                subscriptions=subscriptions,
                identity_key=identity_key,
                one_time_keys=one_time_keys,
            )

            self.log.info(
                f"Successfully login user at {conn.remote_address[0]}:"
                + f"{conn.remote_address[1]} with public key {message}"
                + f" (digest: {message})"
            )

        except ServerAuthFailed:
            self.log.error(
                f"User authentication failed: {conn.remote_address[0]}:"
                + f"{conn.remote_address[1]}"
            )
            # Terminate the connection with application error code
            await conn.close(code=3000, reason="Authentication failed")
        except Exception:
            self.log.error("Unexpected error occurred!", exc_info=True)
