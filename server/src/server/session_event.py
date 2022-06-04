"""Type representing a session event."""

from enum import IntEnum, auto, unique
from typing import Any, Dict, Union

from common.messages_types import AbstractMessage


@unique
class EventType(IntEnum):
    """Session event type."""

    MESSAGE = auto()
    LOGIN = auto()
    LOGOUT = auto()


class SessionEvent:
    """A session event."""

    def __init__(
        self,
        event_type: EventType,
        payload: Union[AbstractMessage, Dict[str, Any]] = None,
    ) -> None:
        """Instantiate a new event."""
        self.event_type = event_type
        self.payload = payload


class MessageEvent(SessionEvent):
    """An incoming message event."""

    def __init__(self, message: AbstractMessage) -> None:
        """Initialize an incoming message event."""
        super().__init__(EventType.MESSAGE, message)


class LoginEvent(SessionEvent):
    """A user login event."""

    def __init__(self, peer_id: str) -> None:
        """Initialize a login event."""
        super().__init__(EventType.LOGIN, {"peer": peer_id})


class LogoutEvent(SessionEvent):
    """A user logout event."""

    def __init__(self, peer_id: str) -> None:
        """Initialize a logout event."""
        super().__init__(EventType.LOGOUT, {"peer": peer_id})
