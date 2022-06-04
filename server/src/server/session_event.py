"""Type representing a session event."""

from enum import IntEnum, auto, unique
from typing import Any, Dict


@unique
class EventType(IntEnum):
    """Session event type."""

    SEND_QUESTION = auto()


class SessionEvent:
    """A session event."""

    def __init__(
        self,
        event_type: EventType,
        payload: Dict[str, Any] = None,
    ) -> None:
        """Instantiate a new event."""
        self.event_type = event_type
        self.payload = payload


class SendQuestionEvent(SessionEvent):
    """Send question event."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        """Initialize send question message event."""
        super().__init__(EventType.SEND_QUESTION, payload)
