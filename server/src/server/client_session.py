"""Class representing a client session with the server."""

import asyncio
from typing import Dict, List

import websockets.server as ws


class ClientSession:
    """Class representing a client session with the server."""

    def __init__(
        self,
        conn: ws.WebSocketServerProtocol,
        user_id: str,
    ) -> None:
        """Initialize a client session."""
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.connection = conn
        self.user_id = user_id
        self.hostname = conn.remote_address[0]
        self.port = conn.remote_address[1]