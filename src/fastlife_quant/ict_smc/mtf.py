"""Analyse multi-timeframe sans look-ahead.

Une bougie HTF n'est utilisable qu'APRES sa cloture : `available_time =
timestamp + duree du timeframe`. Une bougie basse resolution ne voit donc que
les bougies HTF deja closes (jamais la bougie HTF en cours de formation).
"""

from __future__ import annotations

import pandas as pd

from fastlife_quant.data import Timeframe
from fastlife_quant.ict_smc.analyzer import analyze
from fastlife_quant.ict_smc.config import ICTConfig

_BIAS = {1: "bullish", -1: "bearish", 0: "neutral"}


def align_htf(
    ltf: pd.DataFrame, htf: pd.DataFrame, htf_tf: Timeframe, columns: list[str], prefix: str = "htf_"
) -> pd.DataFrame:
    """Ajoute a `ltf` les `columns` du HTF, valeurs de la derniere bougie HTF CLOSE."""
    for name, d in (("ltf", ltf), ("htf", htf)):
        if not d["timestamp"].is_monotonic_increasing:
            raise ValueError(f"{name} doit etre trie par timestamp")
    right = htf[["timestamp", *columns]].copy()
    right["available_time"] = right["timestamp"] + htf_tf.delta
    right = right.drop(columns="timestamp").rename(columns={c: f"{prefix}{c}" for c in columns})
    merged = pd.merge_asof(
        ltf.sort_values("timestamp"), right.sort_values("available_time"),
        left_on="timestamp", right_on="available_time", direction="backward",
    )
    return merged.drop(columns="available_time")


def htf_bias(htf: pd.DataFrame, htf_tf: Timeframe, cfg: ICTConfig = ICTConfig()) -> pd.DataFrame:
    """Biais de structure du HTF apres chaque bougie : bullish / bearish / neutral."""
    res = analyze(htf, htf_tf, cfg)
    return pd.DataFrame(
        {"timestamp": htf["timestamp"].reset_index(drop=True), "bias": [_BIAS[int(t)] for t in res.internal_trend]}
    )


def mtf_context(ltf: pd.DataFrame, htf: pd.DataFrame, htf_tf: Timeframe, cfg: ICTConfig = ICTConfig()) -> pd.DataFrame:
    """`ltf` enrichi de `htf_bias` (biais de la derniere bougie HTF close)."""
    return align_htf(ltf, htf_bias(htf, htf_tf, cfg), htf_tf, ["bias"])
