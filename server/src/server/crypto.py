"""Serverside crytography module."""
import random
from typing import Any, Dict, List, Tuple

from Cryptodome.Hash import SHA3_256

from common.crypto import CURVE_G, CURVE_ORD, CurvePoint, calculate_ballot_mask


class Crypto:
    """Contains cryptographic procedures used by the server."""

    @staticmethod
    def verify_schnorr_signature(
        client_id: int,
        signature: Tuple[int, int],
        exponent: int,
        public_key: Tuple[int, int],
    ) -> bool:
        """
        Check if the client's Schnorr signature is valid,
        i.e. if the ZKP for the first phase passed.
        """
        h = SHA3_256.new()
        h.update(bytes(client_id))
        e = int(h.hexdigest(), base=16) % CURVE_ORD
        signature = CurvePoint(signature)
        public_key = CurvePoint(public_key)
        return signature == CURVE_G * exponent + public_key * e

    @staticmethod
    def get_zkp_challenge() -> int:
        """Get a random challenge value for the ballot validity ZKP."""
        return random.randrange(1, CURVE_ORD)

    @staticmethod
    def verify_ballot_zkp(
        client_id: str,
        public_keys: List[Tuple[int, int]],
        challenge: int,
        proof: Dict[str, Any],
    ) -> bool:
        """Validate a ballot."""
        x = CurvePoint(proof["x"])
        y = CurvePoint(proof["y"])
        a1 = CurvePoint(proof["a1"])
        a2 = CurvePoint(proof["a2"])
        b1 = CurvePoint(proof["b1"])
        b2 = CurvePoint(proof["b2"])
        d1 = proof["d1"]
        d2 = proof["d2"]
        r1 = proof["r1"]
        r2 = proof["r2"]
        ballot_mask = calculate_ballot_mask(int(client_id), public_keys)

        return (
            challenge == (d1 + d2) % CURVE_ORD
            and a1 == CURVE_G * r1 + x * d1
            and b1 == ballot_mask * r1 + y * d1
            and a2 == CURVE_G * r2 + x * d2
            and b2 == ballot_mask * r2 + (y + CURVE_G * (-1 % CURVE_ORD)) * d2
        )
