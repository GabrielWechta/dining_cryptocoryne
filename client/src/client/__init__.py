"""Client application"""

import asyncio
import logging
import logging.handlers
import os
import random

from common.messages_types import AbstractMessage

from .websocket_interface import WebsocketInterface


class Client:
    def __init__(self) -> None:
        """Construct the client object."""
        self._setup_logger()
        self.log = logging.getLogger("logger")

        self.server_hostname = os.environ["SERVER_HOSTNAME"]
        self.server_port = os.environ["PORT"]
        self.certpath = os.environ["SELF_SIGNED_CERT_PATH"]

        self.event_loop = asyncio.get_event_loop()

        self.user_id = hash(random.randint(0, 100_000_000))
        self.websocket_interface = WebsocketInterface(user_id=self.user_id)

    def run(self) -> None:
        """Run client."""

        # Connect to the server
        self.event_loop.run_until_complete(
            asyncio.gather(  # noqa: FKA01
                self.websocket_interface.connect(
                    url=f"wss://{self.server_hostname}:{self.server_port}",
                    certpath=self.certpath,
                ),
                self._handle_downstream_message(),
            )
        )

    @staticmethod
    def _setup_logger() -> None:
        """Setup logger."""
        logger = logging.getLogger("logger")

        # Prepare the formatter
        formatter = logging.Formatter(
            fmt="[%(levelname)s] %(asctime)s %(message)s",
        )

        # Create a handler
        handler = logging.handlers.RotatingFileHandler(
            filename=os.environ["CLIENT_LOGFILE_PATH"],
        )

        # Associate the formatter with the handler...
        handler.setFormatter(formatter)
        # ...and the handler with the logger
        logger.addHandler(handler)

        logger.setLevel(logging.INFO)

    async def _handle_downstream_message(self) -> None:
        """Handle downstream user messages."""
        while True:
            message = await self.websocket_interface.receive_message()

            self.log.debug(f"Received message from {message.header.sender}")

    async def _handle_upstream_message(self, message: AbstractMessage) -> None:
        """Handle an upstream message."""
        self.log.debug(f"Sending message of type {message.msg_id}")

        await self.websocket_interface.send_message(message)
