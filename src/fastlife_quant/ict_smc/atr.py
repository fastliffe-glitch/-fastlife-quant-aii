from __future__ import annotations

import pandas as pd


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcule l'ATR sans utiliser de donnees futures.

    Definition: True Range max(high-low, abs(high-prev_close), abs(low-prev_close))
    puis moyenne mobile simple sur la periode demandee.
    """
    if df.empty:
        return pd.Series(dtype=float)
    if not {"high", "low", "close"}.issubset(df.columns):
        raise ValueError("df doit contenir high, low et close")
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    tr = tr.fillna(0.0)
    if period <= 0:
        raise ValueError("period doit etre > 0")
    return tr.rolling(window=period, min_periods=period).mean().bfill()


__all__ = ["compute_atr"]
