from Cryptodome.PublicKey import ECC
from common import CURVE_NAME


class Crypto:
    @staticmethod
    def verify_schnorr_signature(client_id: int, signature: str, exponent: int, public_key: str) -> bool:
        """Check if the client's Schnorr signature is valid, i.e. if the ZKP for the first phase passed."""
        # publicznie wysylamy A = g^sekret
        # chcemy wyslac X = g^rand i s = rand - sekret * hash(i)
        # wtedy serwer sprawdza czy g^rand = g^s * A^hash(i)
        signature = ECC.import_key(encoded=signature, curve_name=CURVE_NAME).pointQ
        signature_check = ECC.construct(curve=CURVE_NAME, d=exponent).pointQ
        public_key = ECC.import_key(encoded=public_key, curve_name=CURVE_NAME).pointQ
        return signature == signature_check + public_key * hash(client_id)
