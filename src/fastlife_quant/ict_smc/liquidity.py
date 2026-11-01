"""Liquidite : BSL / SSL, Equal Highs / Lows, Liquidity Sweeps.

- BSL (buy-side) : swing high confirme, non encore pris. SSL : swing low.
- Equal highs/lows : un nouveau swing confirme dont le prix est a moins de
  `equal_tolerance_atr_mult * ATR` d'un niveau actif du meme cote.
- Sweep : la meche depasse le niveau (high > niveau pour BSL) puis le prix
  RE-CLOTURE du bon cote dans les `reclaim_bars` bougies (le sweep est connu a
  cette cloture). Sinon le niveau est "broken" (cassure, pas un sweep).
- `direction` d'un sweep decrit la geometrie du rejet (BSL -> "bearish"), pas une prediction.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from fastlife_quant.ict_smc.config import LiquidityConfig
from fastlife_quant.ict_smc.events import Event, Evidence, bar_evidence
from fastlife_quant.ict_smc.swings import Swing


@dataclass
class LiquidityLevel:
    side: str  # "BSL" | "SSL"
    price: float
    swing_idx: int
    formed_idx: int
    breach_idx: int | None = None
    extreme: float | None = None
    ended_idx: int | None = None
    end_reason: str | None = None  # "swept" | "broken" | None (actif)


@dataclass
class LiquidityResult:
    levels: list[LiquidityLevel]
    events: list[Event]  # EQUAL_HIGHS, EQUAL_LOWS, SWEEP_BSL, SWEEP_SSL


def detect_liquidity(
    df: pd.DataFrame, swings: list[Swing], atr: np.ndarray, cfg: LiquidityConfig = LiquidityConfig()
) -> LiquidityResult:
    n = len(df)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ts = df["timestamp"]
    by_conf: dict[int, list[Swing]] = defaultdict(list)
    for s in swings:
        by_conf[s.confirmed_idx].append(s)

    levels: list[LiquidityLevel] = []
    active: list[LiquidityLevel] = []
    events: list[Event] = []

    def swing_ev(lv: LiquidityLevel, label: str) -> Evidence:
        key = "high" if lv.side == "BSL" else "low"
        return Evidence(label, lv.swing_idx, ts.iloc[lv.swing_idx], {key: lv.price})

    for i in range(n):
        for s in by_conf.get(i, []):
            lv = LiquidityLevel("BSL" if s.kind == "high" else "SSL", s.price, s.idx, i)
            ref = atr[i]
            if np.isfinite(ref) and ref > 0:
                for other in active:
                    if (
                        other.side == lv.side
                        and other.breach_idx is None
                        and lv.swing_idx - other.swing_idx <= cfg.equal_max_separation_bars
                        and abs(other.price - lv.price) <= cfg.equal_tolerance_atr_mult * ref
                    ):
                        kind = "EQUAL_HIGHS" if lv.side == "BSL" else "EQUAL_LOWS"
                        conds = (
                            f"deux swings {'highs' if lv.side == 'BSL' else 'lows'} : #{other.swing_idx} a {other.price:g} et #{lv.swing_idx} a {lv.price:g}",
                            f"ecart = {abs(other.price - lv.price):g} <= {cfg.equal_tolerance_atr_mult:g} x ATR #{i} ({ref:g}) = {cfg.equal_tolerance_atr_mult * ref:g}",
                        )
                        events.append(
                            Event(
                                kind, None, i, ts.iloc[i],
                                (swing_ev(other, "swing_1"), swing_ev(lv, "swing_2")), conds,
                                {"price_1": other.price, "price_2": lv.price, "gap": abs(other.price - lv.price)},
                            )
                        )
            active.append(lv)
            levels.append(lv)

        for lv in list(active):
            if lv.formed_idx == i:
                continue
            bsl = lv.side == "BSL"
            breached = h[i] > lv.price if bsl else l[i] < lv.price
            if lv.breach_idx is None and breached:
                lv.breach_idx = i
                lv.extreme = float(h[i] if bsl else l[i])
            elif lv.breach_idx is not None:
                lv.extreme = float(max(lv.extreme, h[i]) if bsl else min(lv.extreme, l[i]))
            if lv.breach_idx is None:
                continue
            reclaimed = c[i] < lv.price if bsl else c[i] > lv.price
            if reclaimed:
                ref = atr[i]
                pen = abs(lv.extreme - lv.price)
                conds = [
                    f"{lv.side} a {lv.price:g} (swing #{lv.swing_idx}, confirme #{lv.formed_idx})",
                    f"meche #{lv.breach_idx} depasse le niveau ; extreme = {lv.extreme:g} (penetration {pen:g})",
                    f"re-cloture #{i} = {c[i]:g} {'<' if bsl else '>'} {lv.price:g} en {i - lv.breach_idx + 1} bougie(s) <= {cfg.reclaim_bars}",
                ]
                metrics = {
                    "level": lv.price, "extreme": lv.extreme, "penetration": float(pen),
                    "bars_to_reclaim": float(i - lv.breach_idx + 1), "level_age": float(i - lv.swing_idx),
                }
                if np.isfinite(ref) and ref > 0:
                    metrics["penetration_atr"] = float(pen / ref)
                ev = [swing_ev(lv, "swing_niveau"), bar_evidence(df, lv.breach_idx, "bougie_de_meche")]
                if i != lv.breach_idx:
                    ev.append(bar_evidence(df, i, "bougie_de_reclaim"))
                events.append(Event(f"SWEEP_{lv.side}", "bearish" if bsl else "bullish", i, ts.iloc[i], tuple(ev), tuple(conds), metrics))
                lv.ended_idx, lv.end_reason = i, "swept"
                active.remove(lv)
            elif i - lv.breach_idx + 1 >= cfg.reclaim_bars:
                lv.ended_idx, lv.end_reason = i, "broken"
                active.remove(lv)

    return LiquidityResult(levels, events)
