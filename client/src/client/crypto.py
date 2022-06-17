"""Clientside crytography module."""
import random
from typing import List, Tuple, Union

from Cryptodome.Hash import SHA3_256

from common.crypto import CURVE_G, CURVE_ORD, CurvePoint


class Crypto:
    """Contains cryptographic procedures used by the client."""

    def __init__(self) -> None:
        """ """
        self.secret = random.randrange(1, CURVE_ORD)
        self.client_id = 0

    def get_public_key(self) -> CurvePoint:
        """Get public key, i.e. g^x, where g is the generator and x is the client's secret."""
        pub_key = CURVE_G * self.secret
        return pub_key

    def get_schnorr_signature(self, client_id: int) -> Tuple[CurvePoint, int]:
        """Prepare a Schnorr signature that serves as a ZKP for knowing the secret."""
        self.client_id = client_id
        k = random.randrange(1, CURVE_ORD)
        r = CURVE_G * k
        h = SHA3_256.new()
        h.update(bytes(client_id))
        e = int(h.hexdigest(), base=16) % CURVE_ORD
        s = (k - self.secret * e) % CURVE_ORD
        return r, s

    def calculate_ballot_mask(
        self, public_keys: List[Tuple[int, int]]
    ) -> Union[CurvePoint, int]:
        """
        Use public keys of other voters to calculate g^yi,
        which serves as a mask for casting votes.
        """
        public_keys = [CurvePoint(key) for key in public_keys]
        previous_keys = sum(public_keys[: self.client_id])
        next_keys = sum(public_keys[(self.client_id + 1) :])
        if previous_keys and next_keys:
            return (previous_keys + next_keys * (-1 % CURVE_ORD)) * self.secret
        return previous_keys * self.secret

    def get_ballot(
        self, vote: int, public_keys: List[Tuple[int, int]]
    ) -> CurvePoint:
        """Mask a vote and return the masked ballot."""
        ballot_mask = self.calculate_ballot_mask(public_keys)
        return ballot_mask + CURVE_G * vote

    def get_tally(self, ballots: List[Tuple[int, int]]) -> int:
        """Count the 'yes' votes."""
        participants_num = len(ballots)
        total = sum(CurvePoint(ballot) for ballot in ballots)
        for t in range(participants_num + 1):
            if total == CURVE_G * t:
                return t
        return -1
