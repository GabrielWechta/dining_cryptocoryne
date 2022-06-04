"""Downstream traffic handler."""

import logging
from typing import Any, Dict

from common.messages_types import SendQuestion, msg_send
from server.client_session import ClientSession

from .session_event import EventType, SessionEvent


class SessionDownstreamHandler:
    """Downstream events handler.

    Aggregates methods related to handling downstream traffic, i.e.
    from the server to the client.
    """

    def __init__(
        self,
        sessions: Dict[str, ClientSession],
    ) -> None:
        """Construct the downstream handler."""
        self.log = logging.getLogger("logger")
        # Store a reference to the managed sessions
        self.sessions = sessions
        # Set up event handlers
        self.event_handlers = {
            EventType.SEND_QUESTION: self.__handle_event_send_question,
        }

    async def handle_downstream(self, session: ClientSession) -> None:
        """Handle downstream traffic, i.e. server to client.

        This API is exposed to the session manager so that it
        can dispatch downstream handling here.
        """
        while True:
            event: SessionEvent = await self.__get_event(session)
            if event.event_type in self.event_handlers.keys():
                # Call a registered event handler
                # await self.event_handlers[event.event_type](event, session)
                await self.event_handlers[event.event_type](event, session)
            else:
                self.log.warning(f"Unsupported event type: {event.event_type}")

    async def send_event(self, event: SessionEvent, user_id: str) -> None:
        """Send an event.

        The event shall be handled in the relevant session's
        downstream handler.
        """
        session = self.sessions[user_id]
        await session.event_queue.put(event)

    async def __get_event(self, session: ClientSession) -> SessionEvent:
        """Receive an event from the session's event queue."""
        return await session.event_queue.get()

    async def __handle_event_send_question(
        self, event: SessionEvent, session: ClientSession
    ) -> None:
        """Handle session event of type LOGIN."""
        assert isinstance(event.payload, dict)
        payload: Dict[str, Any] = event.payload

        # Wrap the event in a CANS message and send downstream to the client
        message = SendQuestion(the_question=payload["the_question"])
        await msg_send(message, session.connection)
