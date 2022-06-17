"""Crytography module used both by clients and the server."""
from typing import Any, Tuple

from Cryptodome.PublicKey import ECC


class CurvePoint:
    """Class representing a point on the elliptic curve."""

    def __init__(self, coords: Tuple[int, int]) -> None:
        super().__init__()
        self.point = ECC.construct(
            curve=CURVE_NAME, point_x=coords[0], point_y=coords[1]
        ).pointQ

    def __radd__(self, other: Any) -> "CurvePoint":
        if isinstance(other, int) and other == 0:
            return self
        return self + other

    def __add__(self, other: Any) -> "CurvePoint":
        return CurvePoint((self.point + other.point).xy)

    def __mul__(self, other: int) -> "CurvePoint":
        return CurvePoint((self.point * other).xy)

    def __eq__(self, other: Any) -> bool:
        return self.point == other.point

    def to_json(self) -> Tuple[int, int]:
        """Turn the point into a serializable tuple."""
        return int(self.point.x), int(self.point.y)


CURVE_NAME = "p256"
CURVE_ORD = 115792089210356248762697446949407573529996955224135760342422259061068512044369
CURVE_G = CurvePoint(
    (
        48439561293906451759052585252797914202762949526041747995844080717082404635286,
        36134250956749795798585127919587881956611106672985015071877198253568414405109,
    )
)
