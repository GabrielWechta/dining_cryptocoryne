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


class UserLogin(AbstractMessage):
    """User login message."""

    def __init__(self) -> None:
        """Create a user login message to server."""
        super().__init__()
        self.header.msg_id = MsgId.USER_LOGIN


class AbstractMessageException(Exception):
    """Abstract exception type."""

    pass


class DeserializationError(AbstractMessageException):
    """Error thrown on deserialization failure."""

    pass


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
