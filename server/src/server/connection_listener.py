"""Client connection entry point.

Listen for connection on a public port and dispatch
them to connection handlers/callbacks.
"""

import asyncio
import logging
import ssl

import websockets.server as ws

from .session_manager_server import SessionManager
from common.messages_types import msg_recv

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
        self.log.debug(
            f"Accepted connection from {conn.remote_address[0]}:"
            f"{conn.remote_address[1]}"
        )
        first_msg = await msg_rcv(conn)
        # user_id = first_msg.payload["user_id"]

        # delegate further handling to the session manager
        await self.session_manager.authed_user_entry(
            conn=conn,
            user_id=user_id,
        )