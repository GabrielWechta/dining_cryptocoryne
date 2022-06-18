"""Type representing a session event."""

from enum import IntEnum, auto, unique
from typing import Any, Dict


@unique
class EventType(IntEnum):
    """Session event type."""

    SEND_QUESTION = auto()
    ZKP_FOR_BALLOT_CHALLENGE = auto()
    ZKP_FOR_BALLOT_ACC = auto()
    SEND_BALLOTS = auto()


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


class ZKPForBallotChallengeEvent(SessionEvent):
    """Challenge of ZKP for ballot event."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        """Initialize challenge of ZKP for ballot event."""
        super().__init__(EventType.ZKP_FOR_BALLOT_CHALLENGE, payload)


class ZKPForBallotAccEvent(SessionEvent):
    """Acceptance of ZKP for ballot event."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        """Initialize acceptance of ZKP for ballot event."""
        super().__init__(EventType.ZKP_FOR_BALLOT_ACC, payload)


class SendBallotsEvent(SessionEvent):
    """Send masked ballots event."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        """Initialize send ballots event."""
        super().__init__(EventType.SEND_BALLOTS, payload)
