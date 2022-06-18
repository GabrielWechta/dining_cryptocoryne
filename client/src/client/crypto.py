"""Clientside crytography module."""
import random
from typing import Any, Dict, List, Tuple

from Cryptodome.Hash import SHA3_256

from common.crypto import CURVE_G, CURVE_ORD, CurvePoint, calculate_ballot_mask


class Crypto:
    """Contains cryptographic procedures used by the client."""

    def __init__(self) -> None:
        """ """
        self.secret = random.randrange(1, CURVE_ORD)
        self.client_id: Any = None
        self.vote: Any = None
        self.ballot_zkp_data: Any = None

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

    def get_ballot(
        self, vote: int, public_keys: List[Tuple[int, int]]
    ) -> Tuple[CurvePoint, Dict[str, CurvePoint]]:
        """Mask a vote and return the masked ballot."""
        self.vote = vote
        ballot_mask = calculate_ballot_mask(self.client_id, public_keys)
        proof = self.get_first_phase_ballot_validity_proof(vote, ballot_mask)
        return ballot_mask * self.secret + CURVE_G * vote, proof

    def get_first_phase_ballot_validity_proof(
        self, vote: int, ballot_mask: CurvePoint
    ) -> Dict[str, CurvePoint]:
        """Prepare a dict of values for the first phase of ballot validity ZKP."""
        w = random.randrange(1, CURVE_ORD)
        r = random.randrange(1, CURVE_ORD)
        d = random.randrange(1, CURVE_ORD)
        self.ballot_zkp_data = w, r, d
        x = CURVE_G * self.secret
        y = ballot_mask * self.secret + CURVE_G * vote
        a1 = CURVE_G * r + x * d
        a2 = CURVE_G * w
        b1 = ballot_mask * r + (y + CURVE_G * ((vote - 1) % CURVE_ORD)) * d
        b2 = ballot_mask * w
        proof = {"x": x, "y": y}
        if vote == 1:
            proof.update({"a1": a1, "a2": a2, "b1": b1, "b2": b2})
        else:
            proof.update({"a1": a2, "a2": a1, "b1": b2, "b2": b1})
        return proof

    def get_second_phase_ballot_validity_proof(
        self, challenge: int
    ) -> Dict[str, int]:
        """Prepare a dict of values for the second phase of ballot validity ZKP."""
        w, r, d = self.ballot_zkp_data
        d2 = (challenge - d) % CURVE_ORD
        r2 = (w - self.secret * d2) % CURVE_ORD
        if self.vote == 1:
            proof = {"d1": d, "d2": d2, "r1": r, "r2": r2}
        else:
            proof = {"d1": d2, "d2": d, "r1": r2, "r2": r}
        return proof

    def get_tally(self, ballots: List[Tuple[int, int]]) -> int:
        """Count the 'yes' votes."""
        participants_num = len(ballots)
        total = sum(CurvePoint(ballot) for ballot in ballots)
        for t in range(participants_num + 1):
            if total == CURVE_G * t:
                return t
        return -1
