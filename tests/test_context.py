from __future__ import annotations

import pandas as pd

from fastlife_quant.ict_smc import (
    detect_bearish_order_block,
    detect_bullish_order_block,
    detect_breaker_block,
    detect_mitigation,
)


def make_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-05 00:00", periods=8, freq="5min", tz="UTC"),
            "open": [100, 99, 98, 99, 100, 101, 102, 103],
            "high": [101, 100, 99, 100, 101, 102, 103, 104],
            "low": [98, 97, 96, 97, 98, 99, 100, 101],
            "close": [99, 98, 97, 98, 99, 100, 101, 102],
            "timeframe": ["M5"] * 8,
        }
    )


def test_order_blocks_and_mitigation_detected():
    df = make_df()
    assert detect_bullish_order_block(df, 5) is not None
    assert detect_bearish_order_block(df, 5) is not None
    assert detect_mitigation(df, 5) is not None
    assert detect_breaker_block(df, 5) is not None
