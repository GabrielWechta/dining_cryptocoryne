"""Serverside crytography module."""
from typing import Tuple

from Cryptodome.Hash import SHA3_256

from common.crypto import CURVE_G, CURVE_ORD, CurvePoint


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
