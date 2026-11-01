from __future__ import annotations

import pandas as pd

from fastlife_quant.ict_smc import (
    detect_bsl,
    detect_equal_highs,
    detect_equal_lows,
    detect_inducement,
    detect_liquidity_sweep,
    detect_ssl,
)


def make_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-05 00:00", periods=6, freq="5min", tz="UTC"),
            "open": [100.0, 101.0, 101.5, 102.0, 103.0, 104.0],
            "high": [101.0, 102.0, 102.5, 103.0, 104.0, 105.0],
            "low": [99.0, 100.0, 100.5, 101.0, 102.0, 103.0],
            "close": [100.5, 101.5, 102.0, 102.5, 103.5, 104.5],
            "timeframe": ["M5"] * 6,
        }
    )


def test_bsl_and_ssl_detected():
    df = make_df()
    assert detect_bsl(df, 3) is not None
    assert detect_ssl(df, 3) is not None


def test_equal_highs_and_lows():
    df = make_df().copy()
    df.loc[1, "high"] = df.loc[0, "high"]
    df.loc[3, "low"] = df.loc[2, "low"]
    assert detect_equal_highs(df, 1) is not None
    assert detect_equal_lows(df, 3) is not None


def test_liquidity_sweep_and_inducement():
    df = make_df()
    assert detect_liquidity_sweep(df, 3) is not None
    assert detect_inducement(df, 3) is not None


def test_missing_or_invalid_data_is_handled():
    df = pd.DataFrame({"timestamp": [], "open": [], "high": [], "low": [], "close": [], "timeframe": []})
    assert detect_bsl(df, 0) is None
    assert detect_ssl(df, 0) is None
