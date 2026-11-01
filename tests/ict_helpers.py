"""Outils de test ICT/SMC. Les series sont des FIXTURES synthetiques deterministes :
elles verifient la logique technique, elles n'ont AUCUNE valeur statistique."""

import numpy as np
import pandas as pd

from fastlife_quant.ict_smc import ATRConfig, ICTConfig, SwingConfig

# (open, high, low, close). Scenario haussier puis CHoCH baissier (swings 1/1).
SCENARIO = [
    (10, 11, 9, 10),        # 0
    (10, 13, 10, 12),       # 1  swing high 13 (confirme a 2)
    (12, 12, 10.5, 11),     # 2
    (11, 12, 9.5, 10),      # 3  bougie baissiere ; swing low 9.5 (confirme a 4)
    (10, 12, 10, 11.5),     # 4
    (11.5, 14, 11, 13.5),   # 5  close 13.5 > 13 : BOS haussier initial
    (13.5, 13.8, 12.5, 13), # 6  swing high 14 (confirme a 6)
    (13, 13.5, 12, 12.2),   # 7  swing low 12 (confirme a 8)
    (12.2, 13.9, 12.2, 13.8),  # 8
    (13.8, 15, 13.5, 14.8), # 9  close 14.8 > 14 : BOS haussier
    (14.8, 14.9, 11, 11.5), # 10 close 11.5 < 12 : CHoCH baissier (+ MSS si deplacement)
]


def frame(rows, start="2026-01-05 00:00", freq="5min"):
    ts = pd.date_range(start, periods=len(rows), freq=freq, tz="UTC")
    a = np.array(rows, dtype=float)
    return pd.DataFrame({"timestamp": ts, "open": a[:, 0], "high": a[:, 1], "low": a[:, 2], "close": a[:, 3]})


def mirror(rows, k=40):
    return [(k - o, k - l, k - h, k - c) for (o, h, l, c) in rows]


def small_cfg(**kw):
    """Config a petite echelle pour series courtes (swings 1/1, ATR 3)."""
    base = dict(swing=SwingConfig(1, 1), external_swing=SwingConfig(1, 1), atr=ATRConfig(3))
    base.update(kw)
    return ICTConfig(**base)


def random_walk(n=400, seed=7):
    rng = np.random.default_rng(seed)
    close = 2000 + np.cumsum(rng.normal(0, 1.5, n))
    open_ = np.concatenate([[close[0]], close[:-1]])
    rng2 = np.random.default_rng(seed + 1)
    high = np.maximum(open_, close) + np.abs(rng2.normal(0, 0.6, n))
    low = np.minimum(open_, close) - np.abs(rng2.normal(0, 0.6, n))
    return pd.DataFrame(
        {"timestamp": pd.date_range("2026-01-05", periods=n, freq="5min", tz="UTC"),
         "open": open_, "high": high, "low": low, "close": close}
    )
