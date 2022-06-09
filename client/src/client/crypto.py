from __future__ import annotations
from Cryptodome.PublicKey import ECC
from common import CURVE_NAME


class Crypto:
    def __init__(self):
        self.secret = ECC.generate(curve=CURVE_NAME)

    def get_public_key(self) -> str:
        """Get public key, i.e. g^x, where g is the generator and x is the client's secret."""
        return self.secret.public_key().export_key(format="OpenSSH")

    def get_schnorr_signature(self, client_id) -> tuple[str, int]:
        """Prepare a Schnorr signature that serves as a ZKP for knowing the secret."""
        # publicznie wysylamy A = g^sekret
        # chcemy wyslac X = g^rand i s = rand - sekret * hash(i)
        # wtedy serwer sprawdza czy g^rand = g^s * A^hash(i)
        r = ECC.generate(curve=CURVE_NAME)
        s = r.d - self.secret.d * hash(client_id)
        return r.public_key().export_key(format="OpenSSH"), int(s)
