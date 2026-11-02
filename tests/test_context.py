from __future__ import annotations

import pandas as pd

from fastlife_quant.ict_smc import detect_discount, detect_equilibrium, detect_ote, detect_premium, multi_timeframe_analysis


def make_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-05 00:00", periods=5, freq="5min", tz="UTC"),
            "open": [100, 101, 102, 103, 104],
            "high": [105, 106, 107, 108, 109],
            "low": [95, 96, 97, 98, 99],
            "close": [103, 104, 105, 106, 107],
            "timeframe": ["M5"] * 5,
        }
    )


def test_premium_discount_equilibrium_and_ote():
    df = make_df()
    assert detect_premium(df, 4) is not None
    assert detect_discount(df, 4) is not None
    assert detect_equilibrium(df, 4) is not None
    assert detect_ote(df, 4) is not None


def test_multitimeframe_summary():
    summary = multi_timeframe_analysis({"M5": make_df(), "H1": make_df()})
    assert "M5" in summary and "H1" in summary
