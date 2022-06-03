"""Client connection entry point.

Listen for connection on a public port and dispatch
them to connection handlers/callbacks.
"""

import asyncio
import logging
import ssl

import websockets.server as ws

from common.messages_types import msg_recv

from .session_manager_server import SessionManager


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
        self.session_manager = SessionManager()
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

    # async def login_user(
    #     self, conn: ws.WebSocketServerProtocol
    # ) -> Tuple[str, List[str], str, Dict[str, str]]:
    #     """Run authentication protocol with the user."""
    #     # Await commitment message
    #     commit_message: SchnorrCommit = await cans_recv(conn)
    #     public_key = commit_message.payload["public_key"]
    #     commitment = commit_message.payload["commitment"]
    #
    #     # Send back the challenge
    #     challenge = get_schnorr_challenge()
    #     challenge_message = SchnorrChallenge(challenge)
    #     await cans_send(challenge_message, conn)
    #
    #     # Wait for the response
    #     response_message: SchnorrResponse = await cans_recv(conn)
    #     response = response_message.payload["response"]
    #
    #     if schnorr_verify(
    #         public_key=public_key,
    #         commitment=commitment,
    #         challenge=challenge,
    #         response=response,
    #     ):
    #         return (
    #             public_key,
    #             response_message.payload["subscriptions"],
    #             response_message.payload["identity_key"],
    #             response_message.payload["one_time_keys"],
    #         )
    #     else:
    #         raise ServerAuthFailed("Authentication failed!")

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

            self.log.info(
                f"Successfully authenticated user at {conn.remote_address[0]}:"
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
