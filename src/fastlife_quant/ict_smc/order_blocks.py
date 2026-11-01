"""Order Blocks.

Definition (tous les seuils sont configurables, voir OrderBlockConfig) :
1. Deplacement haussier a la bougie d : `displacement_bars` bougies consecutives
   haussieres se terminant en d, dont le mouvement net (close[d] - open[debut])
   >= displacement_atr_mult * ATR(bougie avant le debut du deplacement).
2. OB haussier = la derniere bougie BAISSIERE avant le debut du deplacement
   (recherche sur max_lookback_bars). Zone = corps ou amplitude de cette bougie.
   Symetrique pour le baissier.
3. Confirmation (si require_structure_break) : un evenement de structure de meme
   direction, de type dans accepted_breaks, survient dans [d, d + confirm_window].
   L'OB n'est CONNU qu'a cette bougie de confirmation (sinon a d).
4. Rejet si une cloture traverse deja la zone (contre l'OB) avant la confirmation.
Un OB (bougie, direction) n'est enregistre qu'une fois (premier deplacement).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fastlife_quant.ict_smc.config import OrderBlockConfig
from fastlife_quant.ict_smc.events import Event, bar_evidence


def detect_order_blocks(
    df: pd.DataFrame,
    atr: np.ndarray,
    structure_events: list[Event],
    cfg: OrderBlockConfig = OrderBlockConfig(),
) -> list[Event]:
    n = len(df)
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ts = df["timestamp"]
    N = cfg.displacement_bars

    out: list[Event] = []
    seen: set[tuple[int, str]] = set()

    for d in range(N, n):
        start = d - N + 1
        ref = atr[start - 1]
        if not (np.isfinite(ref) and ref > 0):
            continue
        for sign, direction in ((1, "bullish"), (-1, "bearish")):
            if not all(sign * (c[k] - o[k]) > 0 for k in range(start, d + 1)):
                continue
            net = sign * (c[d] - o[start])
            if net < cfg.displacement_atr_mult * ref:
                continue
            j = next(
                (k for k in range(start - 1, max(-1, start - 1 - cfg.max_lookback_bars), -1) if sign * (c[k] - o[k]) < 0),
                None,
            )
            if j is None or (j, direction) in seen:
                continue
            seen.add((j, direction))

            if cfg.zone == "body":
                zl, zh = min(o[j], c[j]), max(o[j], c[j])
            else:
                zl, zh = l[j], h[j]

            conf_ev = None
            if cfg.require_structure_break:
                conf_ev = next(
                    (
                        e for e in structure_events
                        if e.direction == direction and e.kind in cfg.accepted_breaks
                        and d <= e.detected_idx <= d + cfg.confirm_window_bars
                    ),
                    None,
                )
                if conf_ev is None:
                    continue
                det = conf_ev.detected_idx
            else:
                det = d

            closes = c[j + 1 : det + 1]
            violated = (closes < zl).any() if sign == 1 else (closes > zh).any()
            if violated:
                continue

            conds = [
                f"deplacement {direction} : {N} bougie(s) #{start}..#{d}, mouvement net = {net:g} = {net / ref:.2f} ATR (ATR #{start - 1} = {ref:g}) >= {cfg.displacement_atr_mult:g} ATR",
                f"derniere bougie {'baissiere' if sign == 1 else 'haussiere'} avant le deplacement : #{j} (open {o[j]:g}, close {c[j]:g})",
                f"zone ({cfg.zone}) = [{zl:g}, {zh:g}]",
            ]
            ev = [bar_evidence(df, j, "bougie_OB")]
            ev += [bar_evidence(df, k, f"deplacement_{k}") for k in range(start, d + 1)]
            metrics = {
                "zone_low": float(zl), "zone_high": float(zh), "ob_idx": float(j),
                "displacement_atr": float(net / ref), "atr": float(ref),
            }
            if conf_ev is not None:
                conds.append(
                    f"confirmation : {conf_ev.kind} {direction} a la bougie #{conf_ev.detected_idx} (niveau {conf_ev.metrics.get('level'):g})"
                )
                ev.extend(conf_ev.evidence)
                metrics["confirm_idx"] = float(conf_ev.detected_idx)
            else:
                conds.append("confirmation de structure non exigee (require_structure_break=False)")
            conds.append(f"aucune cloture ne traverse la zone entre #{j + 1} et #{det}")
            out.append(Event("ORDER_BLOCK", direction, det, ts.iloc[det], tuple(ev), tuple(conds), metrics))

    out.sort(key=lambda e: (e.detected_idx, e.metrics["ob_idx"], e.direction))
    return out
