"""Upstream traffic handler."""
import asyncio
import logging
from asyncio import Event
from typing import Dict

from common import NUM_PARTICIPANTS
from common.messages_types import AbstractMessage, MsgId, msg_recv
from server.client_session import ClientSession
from server.session_event import (
    SendBallotsEvent,
    SessionEvent,
    ZKPForBallotAccEvent,
    ZKPForBallotChallengeEvent,
)

from .crypto import Crypto


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
        self.message_handlers = {
            MsgId.MASKED_BALLOT: self._steer_message_masked_ballot,
            MsgId.BALLOT_ZKP: self._steer_message_ballot_zkp,
        }

    async def handle_upstream(self, session: ClientSession) -> None:
        """Handle upstream traffic, i.e. client to server.

        This API is exposed to the session manager so that it
        can dispatch upstream handling here.
        """
        while True:
            # Receive a message from the socket
            message = await msg_recv(session.connection)

            msg_id = message.header.msg_id

            # Validate the message header
            if msg_id in self.message_handlers.keys():
                # Call the relevant handler
                await self.message_handlers[msg_id](message, session)
            else:
                self.log.warning(
                    "Received malformed message from"
                    + f" Client {session.user_id}:"
                    + f" {message.header.msg_id=},"
                )

    async def __check_ballot_count(self, flag: Event) -> None:
        while True:
            await asyncio.sleep(0.1)
            ballots = [
                session.masked_ballot for session in self.sessions.values()
            ]
            ballot_count = sum(ballot is not None for ballot in ballots)

            if ballot_count >= NUM_PARTICIPANTS and all(
                session.ballot_accepted for session in self.sessions.values()
            ):
                flag.set()
                return

    async def __wait_for_everybody_vote_next_send_all_ballots(
        self, session: ClientSession
    ) -> None:
        self.log.info(
            f"Server starts waiting for all ballots in session "
            f"with Client {session.user_id}."
        )
        flag = asyncio.Event()
        asyncio.create_task(self.__check_ballot_count(flag))
        await flag.wait()

        ballots = [session.masked_ballot for session in self.sessions.values()]
        send_ballots_event = SendBallotsEvent(payload={"ballots": ballots})
        await self.__send_event(send_ballots_event, session)

    async def _steer_message_masked_ballot(
        self, message: AbstractMessage, session: ClientSession
    ) -> None:
        masked_ballot = message.payload["masked_ballot"]
        masked_ballot_proof = message.payload["proof"]
        self.log.info(
            f"Server got {masked_ballot=}, with {masked_ballot_proof=} "
            f"from Client {session.user_id}."
        )
        self.sessions[session.user_id].masked_ballot = masked_ballot
        challenge = Crypto.get_zkp_challenge()
        self.sessions[session.user_id].challenge = challenge
        self.sessions[
            session.user_id
        ].masked_ballot_proof = masked_ballot_proof
        zkp_ballot_challenge_event = ZKPForBallotChallengeEvent(
            payload={"challenge": challenge}
        )
        await self.__send_event(zkp_ballot_challenge_event, session)

    async def _steer_message_ballot_zkp(
        self, message: AbstractMessage, session: ClientSession
    ) -> None:
        masked_ballot_proof = message.payload["proof"]
        self.sessions[session.user_id].masked_ballot_proof.update(
            masked_ballot_proof
        )
        self.log.info(
            f"Server got second part of ZKP, {masked_ballot_proof=} "
            f"from Client {session.user_id}."
        )
        public_keys = [s.public_key for s in self.sessions.values()]
        session = self.sessions[session.user_id]

        acceptance = Crypto.verify_ballot_zkp(
            client_id=session.user_id,
            public_keys=public_keys,
            challenge=session.challenge,
            proof=session.masked_ballot_proof,
        )
        self.sessions[session.user_id].ballot_accepted = acceptance
        zkp_ballot_acc_event = ZKPForBallotAccEvent(
            payload={"acceptance": acceptance}
        )
        await self.__send_event(zkp_ballot_acc_event, session)
        await self.__wait_for_everybody_vote_next_send_all_ballots(session)

    async def __send_event(
        self, event: SessionEvent, session: ClientSession
    ) -> None:
        """Send an event.

        The event shall be handled in the relevant session's
        downstream handler.
        """
        await session.event_queue.put(event)
