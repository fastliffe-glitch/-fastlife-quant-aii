"""Premium / Discount, OTE et Golden Zone.

Sur un range [low, high] : equilibre = milieu. Au-dessus = premium, en dessous =
discount. Les zones OTE / golden sont des retracements mesures depuis la FIN de
la jambe (jambe haussiere low->high : retracement depuis le high vers le bas).

`dealing_range_at` n'utilise que les swings confirmes a la bougie demandee.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastlife_quant.ict_smc.config import FibConfig
from fastlife_quant.ict_smc.swings import Swing


@dataclass(frozen=True)
class PDResult:
    zone: str  # "premium" | "discount" | "equilibrium"
    position: float  # 0 = bas du range, 1 = haut du range
    equilibrium: float


@dataclass(frozen=True)
class DealingRange:
    high: float
    low: float
    high_idx: int
    low_idx: int
    leg: str  # "bullish" si le low precede le high (jambe low->high), sinon "bearish"


def premium_discount(range_high: float, range_low: float, price: float) -> PDResult:
    if range_high <= range_low:
        raise ValueError("range_high doit etre > range_low")
    eq = (range_high + range_low) / 2
    pos = (price - range_low) / (range_high - range_low)
    zone = "premium" if price > eq else "discount" if price < eq else "equilibrium"
    return PDResult(zone, float(pos), float(eq))


def retracement_zone(leg_start: float, leg_end: float, band: tuple[float, float]) -> tuple[float, float]:
    """Bande de prix (bas, haut) du retracement [band[0], band[1]] de la jambe start->end."""
    lo_r, hi_r = band
    if not 0 <= lo_r < hi_r <= 1:
        raise ValueError("band doit verifier 0 <= bas < haut <= 1")
    size = leg_end - leg_start
    a, b = leg_end - lo_r * size, leg_end - hi_r * size
    return (float(min(a, b)), float(max(a, b)))


def ote_zone(rng: DealingRange, cfg: FibConfig = FibConfig()) -> tuple[float, float]:
    start, end = (rng.low, rng.high) if rng.leg == "bullish" else (rng.high, rng.low)
    return retracement_zone(start, end, cfg.ote)


def golden_zone(rng: DealingRange, cfg: FibConfig = FibConfig()) -> tuple[float, float]:
    start, end = (rng.low, rng.high) if rng.leg == "bullish" else (rng.high, rng.low)
    return retracement_zone(start, end, cfg.golden_zone)


def dealing_range_at(swings: list[Swing], idx: int) -> DealingRange | None:
    """Range defini par le dernier swing high et le dernier swing low confirmes a `idx`."""
    known = [s for s in swings if s.confirmed_idx <= idx]
    highs = [s for s in known if s.kind == "high"]
    lows = [s for s in known if s.kind == "low"]
    if not highs or not lows:
        return None
    hi = max(highs, key=lambda s: (s.confirmed_idx, s.idx))
    lo = max(lows, key=lambda s: (s.confirmed_idx, s.idx))
    if hi.price <= lo.price:
        return None
    return DealingRange(hi.price, lo.price, hi.idx, lo.idx, "bullish" if lo.idx < hi.idx else "bearish")
