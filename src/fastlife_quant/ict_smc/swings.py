"""Swing highs / lows avec delai de confirmation.

Un swing high au pivot i exige : high[i] strictement > les `left` bougies de
gauche, et high[i] >= les `right` bougies de droite (a egalite, le PREMIER des
sommets egaux est le swing). Symetrique pour les lows.

Le swing n'est connu qu'a `confirmed_idx = i + right` : toute decision temps reel
a la bougie k ne doit utiliser que les swings avec confirmed_idx <= k.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from fastlife_quant.ict_smc.config import SwingConfig


@dataclass(frozen=True)
class Swing:
    kind: str  # "high" | "low"
    idx: int
    time: pd.Timestamp
    price: float
    confirmed_idx: int
    confirmed_time: pd.Timestamp


def detect_swings(df: pd.DataFrame, cfg: SwingConfig = SwingConfig()) -> list[Swing]:
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    ts = df["timestamp"]
    n, L, R = len(df), cfg.left, cfg.right
    out: list[Swing] = []
    for i in range(L, n - R):
        conf = i + R
        if h[i] > h[i - L : i].max() and h[i] >= h[i + 1 : i + R + 1].max():
            out.append(Swing("high", i, ts.iloc[i], float(h[i]), conf, ts.iloc[conf]))
        if l[i] < l[i - L : i].min() and l[i] <= l[i + 1 : i + R + 1].min():
            out.append(Swing("low", i, ts.iloc[i], float(l[i]), conf, ts.iloc[conf]))
    out.sort(key=lambda s: (s.confirmed_idx, s.idx, s.kind))
    return out


def swings_known_at(swings: list[Swing], idx: int) -> list[Swing]:
    """Swings disponibles a la cloture de la bougie `idx` (sans look-ahead)."""
    return [s for s in swings if s.confirmed_idx <= idx]
