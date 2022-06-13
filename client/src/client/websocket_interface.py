"""Clientside websocket interface."""

import asyncio
import logging
import os
import ssl
import time

import websockets.client as ws

from common.messages_types import (
    AbstractMessage,
    MaskedBallotMessage,
    MsgId,
    UserLoginMessage,
    ZKPForPubKeyMessage,
    msg_recv,
    msg_send,
)


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
        self.participants_number = int(os.environ["PARTICIPANTS_NUMBER"])
        self.always_vote = always_vote

        self.user_id = None  # this will be set up by a message from the server
        self.message_handlers = {
            MsgId.SEND_QUESTION: self._steer_message_send_question,
            MsgId.FINAL_TALLY: self._steer_message_final_tally,
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

            # TODO change public key to real public key
            # C ---> S
            public_key = str(hash(time.time()))
            await msg_send(UserLoginMessage(public_key=public_key), conn)
            self.log.info(f"Client sends login message - {public_key=}.")

            recv_set_user_id_message = await msg_recv(conn)
            user_id = recv_set_user_id_message.payload["user_id"]
            self.user_id = user_id
            self.log.info(f"Client got {user_id=}.")

            # TODO change proof to real proof, I assumed that proof is of type
            #  str, but for me it can be even of type rainbow-star, change in.
            # C ---> S
            proof = "42"
            self.log.info(
                f"Client {self.user_id} sends ZKP for pub key - {proof=}."
            )
            await msg_send(ZKPForPubKeyMessage(proof=proof), conn)

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
                    "Received unexpected message with ID:"
                    + f"{message.header.msg_id}"
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
        self.log.info(
            f"Client {self.user_id} got this question: {the_question}."
        )
        print(the_question)  # printing the question to the User
        vote_str = None
        if self.always_vote is not None:
            vote_repr = 1 if self.always_vote == "yes" else 0

        else:
            while vote_str is None:
                vote_str = input("Your vote:")
                if vote_str.casefold() == "yes".casefold():
                    vote_repr = 1
                elif vote_str.casefold() == "no".casefold():
                    vote_repr = 0
                else:
                    print("Type 'yes' or 'no'.")
                    vote_str = None
        print(vote_repr)

        # TODO compute masked ballot and proof
        masked_ballot = "420"
        masked_ballot_proof = "2137"
        await msg_send(
            MaskedBallotMessage(
                masked_ballot=masked_ballot,
                masked_ballot_proof=masked_ballot_proof,
            ),
            conn,
        )
        self.log.info(
            f"Client {self.user_id} sends masked vote - {masked_ballot=} "
            f"with proof {masked_ballot_proof=}."
        )

        recv_acceptance_message = await msg_recv(conn)
        self.__parse_acceptance(
            recv_acceptance_message=recv_acceptance_message,
            zkp_type="ZKP for ballot",
        )

    async def _steer_message_final_tally(
        self, message: AbstractMessage, conn: ws.WebSocketClientProtocol
    ) -> None:
        """Steer message of type FINAL_TALLY."""
        final_tally = message.payload["final_tally"]
        self.log.info(f"Client {self.user_id} got {final_tally=}.")

        # TODO Compute here voting result
        result_votes = 1
        print(
            "Voting finished with:\n"
            f"{result_votes} - 'yes' votes\n"
            f"{self.participants_number - result_votes} - 'no' votes\n"
        )
