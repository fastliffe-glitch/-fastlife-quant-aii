from __future__ import annotations

import pandas as pd

from fastlife_quant.ict_smc import detect_bearish_fvg, detect_bullish_fvg, detect_displacement, detect_inverse_fvg


def make_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-05 00:00", periods=5, freq="5min", tz="UTC"),
            "open": [100, 101, 99, 101, 100],
            "high": [101, 102, 100, 102, 101],
            "low": [99, 100, 98, 100, 99],
            "close": [100.5, 101.5, 99.5, 101.5, 100.5],
            "timeframe": ["M5"] * 5,
        }
    )


def test_bullish_and_bearish_fvg():
    df = make_df()
    assert detect_bullish_fvg(df, 2) is not None
    assert detect_bearish_fvg(df, 3) is not None


def test_inverse_fvg_and_displacement_detected():
    df = make_df()
    assert detect_inverse_fvg(df, 2) is not None
    assert detect_displacement(df, 3) is not None


def test_prefix_invariance_imbalance():
    df = make_df()
    prefix = df.iloc[:3].copy()
    a = detect_bullish_fvg(prefix, 2)
    b = detect_bullish_fvg(df, 2)
    assert a is not None and b is not None
    assert a.event_type == b.event_type
