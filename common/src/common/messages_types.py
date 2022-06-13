"""Define message formats."""
from enum import IntEnum, auto, unique
from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Any, Dict, Union

from websockets.client import WebSocketClientProtocol
from websockets.server import WebSocketServerProtocol

SerialMessage = str


@unique
class MsgId(IntEnum):
    """Message ID."""

    NO_TYPE = auto()
    USER_LOGIN = auto()
    SET_USER_ID = auto()
    ZKP_FOR_PUB_KEY = auto()
    ZKP_FOR_PUB_KEY_ACC = auto()
    SEND_QUESTION = auto()
    MASKED_BALLOT = auto()
    ZKP_FOR_BALLOT_ACC = auto()
    FINAL_TALLY = auto()


class AbstractMessage:
    """An abstract prototype for a message."""

    def __init__(self) -> None:
        """Create a message."""
        self.header = self.Header()
        self.payload: Dict[str, Any] = {}

    class Header:
        """Message header."""

        def __init__(self) -> None:
            """Create a header."""
            self.sender = None
            self.msg_id: MsgId = MsgId.NO_TYPE


class UserLoginMessage(AbstractMessage):
    """User login message."""

    def __init__(self, public_key: str) -> None:
        """Create a user login message to server with public key."""
        super().__init__()
        self.header.msg_id = MsgId.USER_LOGIN
        self.payload = {"public_key": public_key}


class SetUserIdMessage(AbstractMessage):
    """User set id message."""

    def __init__(self, user_id: int) -> None:
        """Create a server set id message to client."""
        super().__init__()
        self.header.msg_id = MsgId.SET_USER_ID
        self.payload = {"user_id": user_id}


class ZKPForPubKeyMessage(AbstractMessage):
    """Send ZKP for public key message."""

    def __init__(self, proof: str) -> None:
        """Create a client ZKP message to server."""
        super().__init__()
        self.header.msg_id = MsgId.ZKP_FOR_PUB_KEY
        self.payload = {"proof": proof}


class ZKPForPubKeyAccMessage(AbstractMessage):
    """Send acceptance state of ZKP for public key."""

    def __init__(self, acceptance: bool) -> None:
        """Create a server acceptance message to client."""
        super().__init__()
        self.header.msg_id = MsgId.ZKP_FOR_PUB_KEY_ACC
        self.payload = {"acceptance": acceptance}


class SendQuestionMessage(AbstractMessage):
    """Send Question to User message."""

    def __init__(self, the_question: str) -> None:
        """Create a server send question message to client."""
        super().__init__()
        self.header.msg_id = MsgId.SEND_QUESTION
        self.payload = {"the_question": the_question}


class MaskedBallotMessage(AbstractMessage):
    """Send masked vote to the server message."""

    def __init__(self, masked_ballot: str, masked_ballot_proof: str) -> None:
        """Create a client masked vote message to server."""
        super().__init__()
        self.header.msg_id = MsgId.MASKED_BALLOT
        self.payload = {
            "masked_ballot": masked_ballot,
            "masked_ballot_proof": masked_ballot_proof,
        }


class ZKPForBallotAccMessage(AbstractMessage):
    """Send acceptance state of ZKP for ballot."""

    def __init__(self, acceptance: bool) -> None:
        """Create a server acceptance message to client."""
        super().__init__()
        self.header.msg_id = MsgId.ZKP_FOR_BALLOT_ACC
        self.payload = {"acceptance": acceptance}


class FinalTallyMessage(AbstractMessage):
    """Send final tally values message."""

    def __init__(self, final_tally: str) -> None:
        """Create a server final tally message to client."""
        super().__init__()
        self.header.msg_id = MsgId.FINAL_TALLY
        self.payload = {"final_tally": final_tally}


async def msg_recv(
    socket: Union[WebSocketClientProtocol, WebSocketServerProtocol]
) -> AbstractMessage:
    """Receive a message from a socket."""
    serialized_msg = str(await socket.recv())
    return __deserialize(serialized_msg)


async def msg_send(
    msg: AbstractMessage,
    socket: Union[WebSocketClientProtocol, WebSocketServerProtocol],
) -> None:
    """Send message to a socket."""
    serialized_msg = __serialize(msg)
    await socket.send(serialized_msg)


def __serialize(msg: AbstractMessage) -> SerialMessage:
    """Serialize message."""
    return JSONEncoder().encode(
        {"header": msg.header.__dict__, "payload": msg.payload}
    )


def __deserialize(serial: SerialMessage) -> AbstractMessage:
    """Deserialize a serialized message."""
    try:
        deserialized_msg = JSONDecoder().decode(serial)
    except JSONDecodeError:
        raise DeserializationError("JSON deserialization failed.")

    __validate_format(deserialized_msg)

    message = AbstractMessage()
    message.header.sender = deserialized_msg["header"]["sender"]
    message.header.msg_id = deserialized_msg["header"]["msg_id"]
    message.payload = deserialized_msg["payload"]

    return message


def __validate_format(pretender: dict) -> None:
    """Validate the format of a AbstractMessage."""
    template_abstract_msg = AbstractMessage.Header()

    try:
        if "header" not in pretender.keys():
            raise DeserializationError("No valid header.")

        # Assert valid format header
        for header_field in pretender["header"].keys():
            if header_field not in template_abstract_msg.__dict__:
                raise DeserializationError(
                    f"Unexpected header field: {header_field}."
                )
        for expected_field in template_abstract_msg.__dict__.keys():
            if expected_field not in pretender["header"].keys():
                raise DeserializationError(
                    f"Header field missing: {expected_field}."
                )

        # Assert no other fields
        for field in pretender.keys():
            if field not in ["header", "payload"]:
                raise DeserializationError(f"Unexpected field: {field}")

    except Exception as e:
        # Translate any exception to a deserialization error
        raise DeserializationError(f"Unknown error: {e.args}")


class AbstractMessageException(Exception):
    """Abstract exception type."""

    pass


class DeserializationError(AbstractMessageException):
    """Error thrown on deserialization failure."""

    pass
