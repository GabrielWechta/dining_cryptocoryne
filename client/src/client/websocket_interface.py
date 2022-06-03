"""Clientside websocket interface."""

import asyncio
import logging
import ssl

import websockets.client as ws

from common.messages_types import AbstractMessage, MsgId, msg_recv, msg_send


class WebsocketInterface:
    """Interface for (web)socket.

    Manage session with the server, listen for messages from server
    and forward client messages to the server.
    """

    def __init__(self, user_id):
        """Construct a websocket interface instance."""
        self.log = logging.getLogger("cans-logger")
        self.user_id = user_id
        self.message_handlers = {
            MsgId.USER_LOGIN: self._handle_message_user_login,
        }
        self.upstream_message_queue: asyncio.Queue = asyncio.Queue()
        self.downstream_message_queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, url: str, certpath: str) -> None:
        """Connect to the server."""
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        ssl_context.load_verify_locations(certpath)
        ssl_context.check_hostname = False

        self.log.debug(f"Connecting to the server at {url}...")

        async with ws.connect(url, ssl=ssl_context) as conn:
            self.log.debug("Successfully connected to the server...")
            await asyncio.gather(
                self._handle_upstream(conn),
                self._handle_downstream(conn),
            )

    async def send_message(self, message: AbstractMessage) -> None:
        """Send an outgoing message to server."""
        await self.upstream_message_queue.put(message)

    async def receive_message(self) -> AbstractMessage:
        """Wait for an incoming message from server."""
        return await self.downstream_message_queue.get()

    async def _handle_upstream(self, conn: ws.WebSocketClientProtocol) -> None:
        """Handle client to server traffic."""
        while True:
            message = await self.upstream_message_queue.get()
            message.header.sender = self.user_id

            await msg_send(message, conn)

    async def _handle_downstream(
        self, conn: ws.WebSocketClientProtocol
    ) -> None:
        """Handle server to client traffic."""
        while True:
            message = await msg_recv(conn)
            self.log.info(message)
            # if message.header.msg_id in self.message_handlers.keys():
            #     # Call a registered handler
            #     await self.message_handlers[message.header.msg_id](message)
            # else:
            #     self.log.warning(
            #         "Received unexpected message with ID:"
            #         + f"{message.header.msg_id}"
            #     )

    async def _handle_message_user_login(
        self, message: AbstractMessage
    ) -> None:
        """Handle message type USER_LOGIN."""
        payload = message.payload["text"]
