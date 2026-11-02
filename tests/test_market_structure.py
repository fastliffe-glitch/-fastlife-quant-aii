from __future__ import annotations

import pandas as pd

from fastlife_quant.ict_smc import detect_bos, detect_choch, detect_swing_high, detect_swing_low


def make_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-05 00:00", periods=9, freq="5min", tz="UTC"),
            "open": [100, 101, 102, 103, 104, 105, 104, 103, 102],
            "high": [101, 102, 103, 104, 105, 106, 105, 104, 103],
            "low": [99, 100, 101, 102, 103, 104, 103, 102, 101],
            "close": [100, 101, 102, 103, 104, 105, 104, 103, 102],
            "timeframe": ["M5"] * 9,
        }
    )


def test_swing_high_detects_local_peak():
    df = make_df()
    ev = detect_swing_high(df, 5)
    assert ev is not None
    assert ev.event_type == "swing_high"
    assert ev.confirmed is True


def test_swing_low_detects_local_trough():
    df = make_df()
    ev = detect_swing_low(df, 7)
    assert ev is not None
    assert ev.event_type == "swing_low"


def test_bos_detects_uptrend_sequence():
    df = make_df()
    ev = detect_bos(df, 5)
    assert ev is not None and ev.direction == "bullish"


def test_choch_detects_trend_change():
    df = make_df()
    ev = detect_choch(df, 5)
    assert ev is not None and ev.direction == "bullish"


def test_prefix_invariance_for_market_structure():
    base = make_df()
    prefix = base.iloc[:6].copy()
    earlier = detect_bos(prefix, 5)
    later = detect_bos(base, 5)
    assert earlier is not None
    assert later is not None
    assert earlier.event_type == later.event_type
    assert earlier.direction == later.direction
