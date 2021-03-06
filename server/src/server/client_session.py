"""Class representing a client session with the server."""

import asyncio
from typing import Optional, Tuple

import websockets.server as ws


class ClientSession:
    """Class representing a client session with the server."""

    def __init__(
        self,
        conn: ws.WebSocketServerProtocol,
        user_id: str,
        public_key: Tuple[int, int],
        public_key_proof: Tuple[int, int],
    ) -> None:
        """Initialize a client session."""
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.connection = conn
        self.user_id = user_id
        self.hostname = conn.remote_address[0]
        self.port = conn.remote_address[1]
        self.public_key = public_key
        self.public_key_proof = public_key_proof
        # those fields will be set during protocol run
        self.masked_ballot: Optional[Tuple[int, int]] = None
        self.masked_ballot_proof = {}
        self.challenge: Optional[int] = None
        self.ballot_accepted = False
