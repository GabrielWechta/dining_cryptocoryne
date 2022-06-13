"""Upstream traffic handler."""
import asyncio
import logging
import os
from asyncio import Event
from typing import Dict

from common.messages_types import AbstractMessage, MsgId, msg_recv
from server.client_session import ClientSession
from server.session_event import (
    SendFinalTallyEvent,
    SessionEvent,
    ZKPForBallotAccEvent,
)


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
        }
        self.participants_number = int(os.environ["PARTICIPANTS_NUMBER"])

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
            if len(self.sessions) >= self.participants_number:
                flag.set()

    async def __wait_for_everybody_vote_next_send_final_tally(
        self, session: ClientSession
    ) -> None:
        self.log.info(
            f"Server starts waiting for all ballots in session "
            f"with Client {session.user_id}."
        )
        flag = asyncio.Event()
        asyncio.create_task(self.__check_ballot_count(flag))
        await flag.wait()

        # TODO get aggregated final tally
        final_tally = "69"
        send_final_tally_event = SendFinalTallyEvent(
            payload={"final_tally": final_tally}
        )
        await self.__send_event(send_final_tally_event, session)
        self.log.info(
            f"Server sent {final_tally=} to Client {session.user_id}."
        )

    async def _steer_message_masked_ballot(
        self, message: AbstractMessage, session: ClientSession
    ) -> None:
        masked_ballot = message.payload["masked_ballot"]
        masked_ballot_proof = message.payload["masked_ballot_proof"]
        self.log.info(
            f"Server got {masked_ballot=}, with {masked_ballot_proof=} "
            f"from Client {session.user_id}."
        )
        # TODO check if proof is good

        # TODO multiply vote aggregator
        acceptance = True
        zkp_ballot_acc_event = ZKPForBallotAccEvent(
            payload={"acceptance": acceptance}
        )
        await self.__send_event(zkp_ballot_acc_event, session)

        await self.__wait_for_everybody_vote_next_send_final_tally(session)

    async def __send_event(
        self, event: SessionEvent, session: ClientSession
    ) -> None:
        """Send an event.

        The event shall be handled in the relevant session's
        downstream handler.
        """
        await session.event_queue.put(event)
