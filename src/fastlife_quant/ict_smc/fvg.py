"""Fair Value Gap (definition ICT classique a trois bougies).

Haussier : low[i] > high[i-2] ; gap = [high[i-2], low[i]].
Baissier : high[i] < low[i-2] ; gap = [high[i], low[i-2]].
Connu a la cloture de la 3e bougie (i). Taille = largeur du gap, aussi exprimee
en ATR (ATR de la bougie i-1, avant la 3e bougie). Filtre : taille >= min_atr_mult * ATR.
Si le filtre est actif et l'ATR indisponible, le FVG n'est pas retenu.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fastlife_quant.ict_smc.config import FVGConfig
from fastlife_quant.ict_smc.events import Event, bar_evidence


def detect_fvgs(df: pd.DataFrame, atr: np.ndarray, cfg: FVGConfig = FVGConfig()) -> list[Event]:
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    ts = df["timestamp"]
    out: list[Event] = []
    for i in range(2, len(df)):
        for direction in ("bullish", "bearish"):
            if direction == "bullish":
                ok, lo, hi = l[i] > h[i - 2], h[i - 2], l[i]
                rule = f"low #{i} = {l[i]:g} > high #{i - 2} = {h[i - 2]:g}"
            else:
                ok, lo, hi = h[i] < l[i - 2], h[i], l[i - 2]
                rule = f"high #{i} = {h[i]:g} < low #{i - 2} = {l[i - 2]:g}"
            if not ok:
                continue
            size = float(hi - lo)
            ref = atr[i - 1]
            have_atr = np.isfinite(ref) and ref > 0
            size_atr = float(size / ref) if have_atr else float("nan")
            if cfg.min_atr_mult > 0:
                if not have_atr or size < cfg.min_atr_mult * ref:
                    continue
            conds = [rule, f"taille du gap = {size:g}"]
            metrics = {"zone_low": float(lo), "zone_high": float(hi), "size": size}
            if have_atr:
                conds.append(f"= {size_atr:.3f} ATR (ATR #{i - 1} = {ref:g}) ; filtre min {cfg.min_atr_mult:g} ATR")
                metrics["size_atr"] = size_atr
            else:
                conds.append("ATR indisponible ; filtre desactive")
            ev = (
                bar_evidence(df, i - 2, "bougie_1"),
                bar_evidence(df, i - 1, "bougie_2"),
                bar_evidence(df, i, "bougie_3"),
            )
            out.append(Event("FVG", direction, i, ts.iloc[i], ev, tuple(conds), metrics))
    return out
