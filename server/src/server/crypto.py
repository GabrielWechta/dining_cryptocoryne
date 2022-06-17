from typing import Tuple

from Cryptodome.Hash import SHA3_256
from Cryptodome.PublicKey import ECC
from common import CURVE_NAME, CURVE_ORD, CURVE_G


class Crypto:
    @staticmethod
    def verify_schnorr_signature(client_id: int, signature: Tuple[int, int], exponent: int, public_key: Tuple[int, int]) -> bool:
        """Check if the client's Schnorr signature is valid, i.e. if the ZKP for the first phase passed."""
        h = SHA3_256.new()
        h.update(bytes(client_id))
        e = int(h.hexdigest(), base=16) % CURVE_ORD
        signature = ECC.construct(curve=CURVE_NAME, point_x=signature[0], point_y=signature[1]).pointQ
        public_key = ECC.construct(curve=CURVE_NAME, point_x=public_key[0], point_y=public_key[1]).pointQ
        return signature == CURVE_G * exponent + public_key * e
