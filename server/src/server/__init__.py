"""Server application."""

import asyncio
import logging
import logging.handlers
import os

from .connection_listener import ConnectionListener


class Server:
    """Server."""

    def __init__(self) -> None:
        """Construct the server object."""
        self._setup_logger()
        self.log = logging.getLogger("logger")
        self.log.info("Server is alive.")
        print("SERVER IS ALIVE")

        self.hostname = os.environ["SERVER_HOSTNAME"]
        self.port = int(os.environ["PORT"])
        self.certpath = os.environ["SERVER_SELF_SIGNED_CERT_PATH"]
        self.keypath = os.environ["SERVER_PRIVATE_KEY_PATH"]

        # Prepare resources
        self.event_loop = asyncio.get_event_loop()
        self.connection_listener = ConnectionListener(
            hostname=self.hostname,
            port=self.port,
            certpath=self.certpath,
            keypath=self.keypath,
        )

    def run(self) -> None:
        """Run the connection listener."""
        self.event_loop.run_until_complete(self.connection_listener.run())

    @staticmethod
    def _setup_logger() -> None:
        """Initialize setup for logger."""
        logger = logging.getLogger("logger")

        # Prepare the formatter
        formatter = logging.Formatter(
            fmt="[%(levelname)s] %(asctime)s %(message)s",
        )

        # Create a rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            filename=os.environ["SERVER_LOGFILE_PATH"], mode="w"
        )

        # Associate the formatter with the handler...
        handler.setFormatter(formatter)
        # ...and the handler with the logger
        logger.addHandler(handler)

        logger.setLevel(logging.INFO)
