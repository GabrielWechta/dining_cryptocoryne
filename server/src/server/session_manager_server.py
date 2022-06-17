"""Serverside session manager."""

import asyncio
import logging
import os
from asyncio import Event
from typing import Any, Dict, Tuple

from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol

from common import NUM_PARTICIPANTS
from server.session_downstream_handler import SessionDownstreamHandler
from server.session_upstream_handler import SessionUpstreamHandler

from .client_session import ClientSession
from .session_event import SendQuestionEvent


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
        self.transcripts: Dict[str, Dict[str, Any]] = {}
        self.the_question = os.environ["THE_QUESTION"]
        # Instantiate the traffic handlers
        self.downstream_handler = SessionDownstreamHandler(
            sessions=self.sessions,
        )
        self.upstream_handler = SessionUpstreamHandler(
            sessions=self.sessions,
        )

    async def add_session_with_user(
        self,
        conn: WebSocketServerProtocol,
        user_id: str,
        public_key: str,
        public_key_proof: Tuple[int, int],
    ) -> None:
        """Handle a logged-in user."""
        # Save the session to have consistent state when
        # sending notifications and talking to the client
        session = ClientSession(
            conn=conn,
            user_id=user_id,
            public_key=public_key,
            public_key_proof=public_key_proof,
        )
        self.sessions[user_id] = session

        await self.__wait_for_everybody_next_send_question(user_id)

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

    async def __check_sessions_count(self, flag: Event) -> None:
        while True:
            await asyncio.sleep(0.1)
            if len(self.sessions) >= NUM_PARTICIPANTS:
                flag.set()
                return

    async def __wait_for_everybody_next_send_question(
        self, user_id: str
    ) -> None:
        self.log.info(
            "Server waits for everybody before sending the question."
        )
        flag = asyncio.Event()
        asyncio.create_task(self.__check_sessions_count(flag))
        await flag.wait()

        send_question_event = SendQuestionEvent(
            payload={
                "the_question": self.the_question,
                "public_keys": [
                    session.public_key for session in self.sessions.values()
                ],
            }
        )

        self.log.info(f"Servers sends question to {user_id}.")
        await self.downstream_handler.send_event(send_question_event, user_id)

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
