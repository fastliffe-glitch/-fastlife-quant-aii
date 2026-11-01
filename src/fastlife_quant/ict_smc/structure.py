"""Structure de marche : BOS, CHoCH, MSS.

Etat causal, bougie par bougie. Le "dernier swing high/low" est le plus recemment
CONFIRME (swing.confirmed_idx <= bougie courante). Chaque swing ne peut etre
casse qu'une fois.

- BOS   : cassure dans le sens de la tendance courante (ou cassure initiale,
          `initial=1`, quand aucune tendance n'est encore etablie).
- CHOCH : cassure contre la tendance courante ; la tendance bascule.
- MSS   : CHoCH dont la bougie de cassure est un deplacement : corps dans le
          sens de la cassure >= mss_displacement_atr_mult * ATR(bougie precedente).
          Emis EN PLUS du CHOCH, sur la meme bougie.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from fastlife_quant.ict_smc.config import StructureConfig
from fastlife_quant.ict_smc.events import Event, bar_evidence
from fastlife_quant.ict_smc.swings import Swing


@dataclass
class StructureResult:
    events: list[Event]
    trend: np.ndarray  # +1 haussier, -1 baissier, 0 indetermine, apres chaque bougie


def _swing_evidence(df: pd.DataFrame, s: Swing, label: str):
    from fastlife_quant.ict_smc.events import Evidence

    return Evidence(label, s.idx, s.time, {"high" if s.kind == "high" else "low": s.price})


def detect_structure(
    df: pd.DataFrame,
    swings: list[Swing],
    atr: np.ndarray,
    cfg: StructureConfig = StructureConfig(),
    scale: str = "internal",
) -> StructureResult:
    n = len(df)
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ts = df["timestamp"]

    by_conf: dict[int, list[Swing]] = defaultdict(list)
    for s in swings:
        by_conf[s.confirmed_idx].append(s)

    last: dict[str, list | None] = {"high": None, "low": None}  # [swing, broken]
    trend = 0
    trend_arr = np.zeros(n, dtype=int)
    events: list[Event] = []

    for i in range(n):
        for s in by_conf.get(i, []):
            last[s.kind] = [s, False]
        ref = atr[i - 1] if i > 0 else np.nan

        for kind, sign in (("high", 1), ("low", -1)):
            st = last[kind]
            if st is None or st[1]:
                continue
            s = st[0]
            if cfg.break_on == "close":
                px, px_name = c[i], "close"
            else:
                px, px_name = (h[i], "high") if sign == 1 else (l[i], "low")
            broke = px > s.price if sign == 1 else px < s.price
            if not broke:
                continue
            st[1] = True

            direction = "bullish" if sign == 1 else "bearish"
            initial = trend == 0
            is_choch = trend not in (0, sign)
            name = "CHOCH" if is_choch else "BOS"
            trend = sign
            body = (c[i] - o[i]) * sign
            body_atr = float(body / ref) if np.isfinite(ref) and ref > 0 else float("nan")
            op = ">" if sign == 1 else "<"
            conds = [
                f"swing {kind} #{s.idx} a {s.price:g} confirme a la bougie #{s.confirmed_idx} (delai {s.confirmed_idx - s.idx})",
                f"{px_name} de #{i} = {px:g} {op} {s.price:g}",
                "cassure initiale (aucune tendance etablie)" if initial else (
                    "cassure CONTRE la tendance precedente : changement de caractere" if is_choch
                    else "cassure DANS le sens de la tendance : continuation"
                ),
            ]
            metrics = {"level": s.price, "break_price": float(px), "initial": float(initial)}
            if np.isfinite(body_atr):
                metrics["body_atr"] = body_atr
            ev_list = (_swing_evidence(df, s, "swing_casse"), bar_evidence(df, i, "bougie_de_cassure"))
            events.append(Event(name, direction, i, ts.iloc[i], ev_list, tuple(conds), {**metrics, "scale_external": float(scale == "external")}))

            if is_choch and np.isfinite(body_atr) and body_atr >= cfg.mss_displacement_atr_mult:
                mconds = conds + [
                    f"deplacement : corps = {body_atr:.2f} ATR >= {cfg.mss_displacement_atr_mult:g} ATR (ATR #{i - 1} = {ref:g})"
                ]
                events.append(Event("MSS", direction, i, ts.iloc[i], ev_list, tuple(mconds), {**metrics, "scale_external": float(scale == "external")}))
        trend_arr[i] = trend

    return StructureResult(events, trend_arr)
