"""Clientside websocket interface."""

import asyncio
import logging
import ssl
import time

import websockets.client as ws

from .crypto import Crypto
from common.messages_types import (
    AbstractMessage,
    AbstractMessageException,
    MsgId,
    UserLogin,
    ZKPForPubKey,
    msg_recv,
    msg_send,
)


class WebsocketInterface:
    """Interface for (web)socket.

    Manage session with the server, listen for messages from server
    and forward client messages to the server.
    """

    def __init__(self) -> None:
        """Construct a websocket interface instance."""
        self.log = logging.getLogger("logger")
        self.always_vote = None

        self.user_id = None
        self.crypto = Crypto()
        self.message_handlers = {
            MsgId.SEND_QUESTION: self._handle_message_send_question,
        }
        self.upstream_message_queue: asyncio.Queue = asyncio.Queue()
        self.downstream_message_queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, url: str, certpath: str) -> None:
        """Connect to the server."""
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        ssl_context.load_verify_locations(certpath)
        ssl_context.check_hostname = False

        self.log.info(f"Connecting to the server at {url}...")
        async with ws.connect(url, ssl=ssl_context) as conn:
            self.log.info(
                "Successfully connected to the server. Running login..."
            )

            public_key = self.crypto.get_public_key()
            await msg_send(UserLogin(public_key=public_key), conn)
            self.log.info(f"Send login - {public_key=}.")

            recv_user_id_message = await msg_recv(conn)
            user_id = recv_user_id_message.payload["user_id"]
            self.user_id = user_id
            self.log.info(f"I got {user_id=}.")

            signature, exponent = self.crypto.get_schnorr_signature(self.user_id)
            await msg_send(ZKPForPubKey(signature=signature, exponent=exponent), conn)
            self.log.info(f"Client {user_id} sends pub key proof - {signature=} {exponent=}.")

            recv_acceptance_message = await msg_recv(conn)
            acceptance = recv_acceptance_message.payload["acceptance"]
            if acceptance is True:
                self.log.info(
                    f"Client {user_id} ZKP for public key was accepted."
                )
            else:
                self.log.error(
                    f"Client {user_id} ZKP for public key was rejected."
                )
                raise AbstractMessageException("ZKP for public key rejected.")

            self.log.info(
                f"Client {user_id} ends handshake and forks to handle"
                + " upstream and downstream concurrently..."
            )
            await asyncio.gather(
                self._handle_upstream(conn),
                self._handle_downstream(conn),
            )

    async def send_message(self, message: AbstractMessage) -> None:
        """Send an outgoing message to server."""
        await self.upstream_message_queue.put(message)

    async def receive_message(self) -> AbstractMessage:
        """Wait for an incoming message from server."""
        return await self.downstream_message_queue.get()

    async def _handle_upstream(self, conn: ws.WebSocketClientProtocol) -> None:
        """Handle client to server traffic."""
        while True:
            message = await self.upstream_message_queue.get()
            message.header.sender = self.user_id

            await msg_send(message, conn)

    async def _handle_downstream(
        self, conn: ws.WebSocketClientProtocol
    ) -> None:
        """Handle downstream traffic, i.e. server to client."""
        while True:
            message = await msg_recv(conn)

            if message.header.msg_id in self.message_handlers.keys():
                # Call a registered handler
                await self.message_handlers[message.header.msg_id](message)
            else:
                self.log.warning(
                    "Received unexpected message with ID:"
                    + f"{message.header.msg_id}"
                )

    async def _handle_message_send_question(
        self, message: AbstractMessage
    ) -> None:
        """Handle message type USER_LOGIN."""
        the_question = message.payload["the_question"]
        print(the_question)
        vote = None
        if self.always_vote is None:
            while vote is None:
                vote = input("Your vote:")
                if vote.casefold() == "yes".casefold():
                    vote_repr = 1
                elif vote.casefold() == "no".casefold():
                    vote_repr = 0
                else:
                    print("Type 'yes' or 'no'.")
                    vote = None
        else:
            vote_repr = self.always_vote

        print(vote_repr)
