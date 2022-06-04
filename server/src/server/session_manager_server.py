"""Serverside session manager."""

import asyncio
import logging
from typing import Callable, Dict

from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol

from server.session_downstream_handler import SessionDownstreamHandler
from server.session_upstream_handler import SessionUpstreamHandler

from .client_session import ClientSession


class SessionsManager:
    """Server session manager.

    Manage client sessions and maintain a mapping between
    client's public keys and event queues corresponding
    to their sessions.
    """

    def __init__(self) -> None:
        """Construct a session manager instance."""
        # Get the logger
        self.log = logging.getLogger("logger")
        self.sessions: Dict[str, ClientSession] = {}
        # Instantiate the traffic handlers
        self.downstream_handler = SessionDownstreamHandler(
            self.sessions,
        )
        self.upstream_handler = SessionUpstreamHandler(
            sessions=self.sessions,
        )

    async def authed_user_entry(
        self,
        conn: WebSocketServerProtocol,
        user_id: str,
    ) -> None:
        """Handle an authenticated user."""
        # Save the session to have consistent state when
        # sending notifications and talking to the client
        session = ClientSession(
            conn=conn,
            user_id=user_id,
        )
        self.sessions[user_id] = session

        # TODO behaviour
        try:
            # Use fork-join semantics to run both upstream and
            # downstream handlers concurrently and wait for both
            # to terminate
            await asyncio.gather(
                self.upstream_handler.handle_upstream(session),
                self.downstream_handler.handle_downstream(session),
            )
        except ConnectionClosed as e:
            await self.__handle_connection_closed(user_id, e)

    async def __handle_connection_closed(
        self, user_id: str, exception: ConnectionClosed
    ) -> None:
        """Handle the client closing the connection."""
        # Remove the client's session
        session = self.sessions.pop(user_id)
        self.log.info(
            f"Connection with {session.hostname}:{session.port}"
            + f" closed with code {exception.code}"
        )
