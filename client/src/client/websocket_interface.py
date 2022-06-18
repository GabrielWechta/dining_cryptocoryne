"""Clientside websocket interface."""

import asyncio
import logging
import ssl
from typing import Any

import websockets.client as ws

from common import NUM_PARTICIPANTS
from common.messages_types import (
    AbstractMessage,
    MaskedBallotMessage,
    MsgId,
    UserLoginMessage,
    ZKPForBallotProofMessage,
    ZKPForPubKeyMessage,
    msg_recv,
    msg_send,
)

from .crypto import Crypto


class RejectZKPException(Exception):
    """Special Exception for bad ZKP."""

    pass


class WebsocketInterface:
    """Interface for (web)socket.

    Manage session with the server, listen for messages from server
    and forward client messages to the server.
    """

    def __init__(self, always_vote: str = None) -> None:
        """Construct a websocket interface instance."""
        self.log = logging.getLogger("logger")
        self.always_vote = always_vote
        self.user_id: Any = (
            None  # this will be set up by a message from the server
        )
        self.crypto = Crypto()
        self.message_handlers = {
            MsgId.SEND_QUESTION: self._steer_message_send_question,
            MsgId.BALLOT_CHALLENGE: self._steer_message_ballot_challenge,
            MsgId.FINAL_BALLOTS: self._steer_message_final_ballots,
        }
        self.upstream_message_queue: asyncio.Queue = asyncio.Queue()
        self.downstream_message_queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, url: str, certpath: str) -> None:
        """Connect to the server."""
        # getting TLS context
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.load_verify_locations(certpath)
        ssl_context.check_hostname = False

        self.log.info(f"Client is connecting to the server at {url}...")
        async with ws.connect(url, ssl=ssl_context) as conn:
            self.log.info(
                "Successfully connected to the server. Running login..."
            )

            public_key = self.crypto.get_public_key()
            await msg_send(UserLoginMessage(public_key=public_key), conn)
            self.log.info(f"Client sends login message - {public_key=}.")

            recv_set_user_id_message = await msg_recv(conn)
            user_id = recv_set_user_id_message.payload["user_id"]
            self.user_id = user_id
            self.log.info(f"Client got {user_id=}.")

            signature, exponent = self.crypto.get_schnorr_signature(
                self.user_id
            )
            self.log.info(
                f"Client {user_id} sends ZKP for pub key - {signature=} {exponent=}."
            )
            await msg_send(
                ZKPForPubKeyMessage(signature=signature, exponent=exponent),
                conn,
            )

            # C <--- S
            recv_acceptance_message = await msg_recv(conn)
            self.__parse_acceptance(
                recv_acceptance_message=recv_acceptance_message,
                zkp_type="ZKP for public key",
            )

            self.log.info(
                f"Client {self.user_id} ends round_1 (handshake) and "
                f"forks to handle upstream and downstream concurrently."
            )

            # Now Server waits for all clients to connect... After all
            # connect server will orchestrate further protocol by sending
            # messages to clients and making them respond accordingly.
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
                await self.message_handlers[message.header.msg_id](
                    message, conn
                )
            else:
                self.log.warning(
                    f"Received unexpected message with ID: {message.header.msg_id}"
                )

    def __parse_acceptance(
        self, recv_acceptance_message: AbstractMessage, zkp_type: str
    ) -> None:
        acceptance = recv_acceptance_message.payload["acceptance"]
        if acceptance is True:
            self.log.info(f"Client {self.user_id} {zkp_type} was accepted.")
        else:
            self.log.error(f"Client {self.user_id} {zkp_type} was rejected.")
            print(f"Your client application provided bad {zkp_type}.")
            raise RejectZKPException(f"{zkp_type} rejected.")

    async def _steer_message_send_question(
        self, message: AbstractMessage, conn: ws.WebSocketClientProtocol
    ) -> None:
        """Steer message of type SEND_QUESTION."""
        the_question = message.payload["the_question"]
        public_keys = message.payload["public_keys"]
        self.log.info(
            f"Client {self.user_id} got this question: {the_question}."
        )
        self.log.info(f"{public_keys=}.")
        print(the_question)  # printing the question to the User
        vote_repr: Any = None
        if self.always_vote is not None:
            vote_repr = 1 if self.always_vote == "yes" else 0

        else:
            vote_mapping = {"yes": 1, "no": 0}
            while vote_repr is None:
                vote_str = input("Your vote:").casefold()
                vote_repr = vote_mapping.get(vote_str)
        print(vote_repr)

        masked_ballot, proof = self.crypto.get_ballot(vote_repr, public_keys)
        await msg_send(
            MaskedBallotMessage(
                masked_ballot=masked_ballot,
                proof=proof,
            ),
            conn,
        )
        self.log.info(
            f"Client {self.user_id} sends masked vote - {masked_ballot=} "
            f"with part one of proof {proof=}."
        )

    async def _steer_message_ballot_challenge(
        self, message: AbstractMessage, conn: ws.WebSocketClientProtocol
    ) -> None:
        challenge = message.payload["challenge"]
        proof = self.crypto.get_second_phase_ballot_validity_proof(challenge)
        await msg_send(
            ZKPForBallotProofMessage(
                proof=proof,
            ),
            conn,
        )
        recv_acceptance_message = await msg_recv(conn)
        self.__parse_acceptance(
            recv_acceptance_message=recv_acceptance_message,
            zkp_type="ZKP for ballot",
        )

    async def _steer_message_final_ballots(
        self, message: AbstractMessage, conn: ws.WebSocketClientProtocol
    ) -> None:
        """Steer message of type FINAL_BALLOTS."""
        ballots = message.payload["ballots"]
        self.log.info(f"Client {self.user_id} got {ballots=}.")
        result_votes = self.crypto.get_tally(ballots)
        print(
            "Voting finished with:\n"
            f"{result_votes} - 'yes' votes\n"
            f"{NUM_PARTICIPANTS - result_votes} - 'no' votes\n"
        )
