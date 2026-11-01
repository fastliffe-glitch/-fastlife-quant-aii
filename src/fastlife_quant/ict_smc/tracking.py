"""Suivi du cycle de vie des zones (FVG, Order Blocks) et zones inversees.

Apres la detection d'une zone [zone_low, zone_high] :
- touched_idx       : premiere bougie dont la meche entre dans la zone
                      (haussier : low <= zone_high ; baissier : high >= zone_low).
- fully_traded_idx  : premiere bougie qui traverse toute la zone par la meche.
- invalidated_idx   : premiere CLOTURE de l'autre cote de la zone
                      (haussier : close < zone_low ; baissier : close > zone_high).
Une zone invalidee donne une zone INVERSEE : IFVG (pour un FVG) ou BREAKER
(pour un Order Block), de direction opposee, connue a la bougie d'invalidation.
Les index sont des dates d'evenement : a la bougie k, ne considerer que idx <= k.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fastlife_quant.ict_smc.events import Event, bar_evidence

_FLIP = {"bullish": "bearish", "bearish": "bullish"}
_INVERSE_KIND = {"FVG": "IFVG", "ORDER_BLOCK": "BREAKER"}


@dataclass(frozen=True)
class ZoneTracking:
    event: Event
    touched_idx: int | None
    fully_traded_idx: int | None
    invalidated_idx: int | None


def track_zones(df: pd.DataFrame, zones: list[Event]) -> list[ZoneTracking]:
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    out = []
    for ev in zones:
        zl, zh = ev.metrics["zone_low"], ev.metrics["zone_high"]
        bull = ev.direction == "bullish"
        touched = traded = inval = None
        for i in range(ev.detected_idx + 1, len(df)):
            if touched is None and ((l[i] <= zh) if bull else (h[i] >= zl)):
                touched = i
            if traded is None and ((l[i] <= zl) if bull else (h[i] >= zh)):
                traded = i
            if (c[i] < zl) if bull else (c[i] > zh):
                inval = i
                break
        out.append(ZoneTracking(ev, touched, traded, inval))
    return out


def derive_inverse_zones(df: pd.DataFrame, trackings: list[ZoneTracking]) -> list[Event]:
    out = []
    ts = df["timestamp"]
    for t in trackings:
        if t.invalidated_idx is None or t.event.kind not in _INVERSE_KIND:
            continue
        ev, i = t.event, t.invalidated_idx
        zl, zh = ev.metrics["zone_low"], ev.metrics["zone_high"]
        close = float(df["close"].iloc[i])
        side = "sous" if ev.direction == "bullish" else "au-dessus de"
        bound = zl if ev.direction == "bullish" else zh
        conds = (
            f"{ev.kind} {ev.direction} #{ev.detected_idx} zone [{zl:g}, {zh:g}] invalidee",
            f"cloture #{i} = {close:g} {side} {bound:g}",
            f"la zone devient {_INVERSE_KIND[ev.kind]} {_FLIP[ev.direction]}",
        )
        out.append(
            Event(
                _INVERSE_KIND[ev.kind], _FLIP[ev.direction], i, ts.iloc[i],
                (*ev.evidence, bar_evidence(df, i, "bougie_d_invalidation")), conds,
                {"zone_low": zl, "zone_high": zh, "origin_idx": float(ev.detected_idx)},
            )
        )
    return out
