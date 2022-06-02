"""Client application"""

import asyncio
import logging
import logging.handlers
import os
from datetime import datetime


class Client:
    def __init__(self) -> None:
        """Construct the client object."""
        self._setup_logger()
        self.server_hostname = os.environ["CANS_SERVER_HOSTNAME"]
        self.server_port = os.environ["CANS_PORT"]
        self.certpath = os.environ["CANS_SELF_SIGNED_CERT_PATH"]

        self.log = logging.getLogger("logger")

        self.event_loop = asyncio.get_event_loop()

        self.session_manager = SessionManager(
            keys=(self.priv_key, self.pub_key),
            account=self.account,
        )

    def run(self) -> None:
        """Run dummy client application."""
        # Connect to the server
        self.event_loop.run_until_complete(
            asyncio.gather(  # noqa: FKA01
                self.session_manager.connect(
                    url=f"wss://{self.server_hostname}:{self.server_port}",
                    certpath=self.certpath,
                    friends=[self.echo_peer_id],
                ),
                self._handle_downstream_message(),
            )
        )

    def _setup_logger(self) -> None:
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
            message = await self.session_manager.receive_message()

            self.log.debug(f"Received message from {message.header.sender}")

    async def _handle_upstream_message(self, message_model: Message) -> None:
        """Handle an upstream message."""
        receiver = message_model.to_user
        message, cookie = self.session_manager.user_message_to(
            receiver.id, message_model.body
        )

        # TODO: Use the cookie to find corresponding acknowledge later

        self.log.debug(
            f"Sending message to {message.header.receiver}"
            + f" (cookie: {cookie})..."
        )

        await self.session_manager.send_message(message)
