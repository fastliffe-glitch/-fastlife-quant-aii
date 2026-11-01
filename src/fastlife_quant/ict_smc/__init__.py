from __future__ import annotations

import pandas as pd


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcule l'ATR sur une serie OHLCV sans jamais utiliser de donnees futures."""
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
    return tr.rolling(window=period, min_periods=period).mean().fillna(method="bfill")


__all__ = ["compute_atr"]
