"""Upstream traffic handler."""

import logging
from typing import Callable, Dict

from common.messages_types import AbstractMessage, msg_recv
from server.client_session import ClientSession
from server.session_event import SessionEvent


class SessionUpstreamHandler:
    """Upstream messages handler.

    Aggregates methods related to handling upstream traffic, i.e.
    from the client to the server.
    """

    def __init__(
        self,
        sessions: Dict[str, ClientSession],
    ) -> None:
        """Construct the upstream handler."""
        self.log = logging.getLogger("logger")
        # Store a reference to the managed sessions
        self.sessions = sessions
        self.message_handlers: Dict[int, Callable] = {}

    async def handle_upstream(self, session: ClientSession) -> None:
        """Handle upstream traffic, i.e. client to server.

        This API is exposed to the session manager so that it
        can dispatch upstream handling here.
        """
        while True:
            # Receive a message from the socket
            message = await msg_recv(session.connection)

            # Validate the message header
            if self.__upstream_message_valid(message, session):
                msg_id = message.header.msg_id
                if msg_id in self.message_handlers.keys():
                    # Call the relevant handler
                    await self.message_handlers[msg_id](message, session)
                else:
                    self.log.warning(f"Unsupported message ID: {msg_id}")
            else:
                self.log.warning(
                    "Received malformed message from"
                    + f" {session.user_id}:"
                    + f" id={message.header.msg_id},"
                    + f" sender={message.header.sender},"
                    + f" receiver={message.header.receiver}"
                )

    def __upstream_message_valid(
        self, message: AbstractMessage, session: ClientSession
    ) -> bool:
        """Validate an inbound message in regard to the current session."""
        return message.header.sender == session.user_id

    async def __send_event(
        self, event: SessionEvent, session: ClientSession
    ) -> None:
        """Send an event.

        The event shall be handled in the relevant session's
        downstream handler.
        """
        await session.event_queue.put(event)
