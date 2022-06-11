import random
from typing import Tuple

from common import CURVE_ORD, CURVE_G
from Cryptodome.Hash import SHA3_256


class Crypto:
    def __init__(self):
        self.secret = random.randrange(1, CURVE_ORD)

    def get_public_key(self) -> Tuple[int, int]:
        """Get public key, i.e. g^x, where g is the generator and x is the client's secret."""
        pub_key = CURVE_G * self.secret
        return int(pub_key.x), int(pub_key.y)

    def get_schnorr_signature(self, client_id) -> Tuple[Tuple[int, int], int]:
        """Prepare a Schnorr signature that serves as a ZKP for knowing the secret."""
        k = random.randrange(1, CURVE_ORD)
        r = CURVE_G * k
        h = SHA3_256.new()
        h.update(bytes(client_id))
        e = int(h.hexdigest(), base=16) % CURVE_ORD
        s = (k - self.secret * e) % CURVE_ORD
        return (int(r.x), int(r.y)), s
