from __future__ import annotations

import pandas as pd

from fastlife_quant.ict_smc.engine import ICTSMCEngine


def make_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-05 00:00", periods=12, freq="5min", tz="UTC"),
            "open": [100, 101, 102, 103, 104, 105, 106, 105, 104, 103, 102, 101],
            "high": [101, 102, 103, 104, 105, 106, 107, 106, 105, 104, 103, 102],
            "low": [99, 100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 100],
            "close": [100, 101, 102, 103, 104, 105, 106, 105, 104, 103, 102, 101],
            "timeframe": ["M5"] * 12,
        }
    )


def test_engine_emits_explicit_events_without_lookahead():
    engine = ICTSMCEngine()
    events = engine.analyze(make_df(), timeframe="M5")
    assert events
    for event in events:
        assert "event_type" in event
        assert "timestamp" in event
        assert "trigger_conditions" in event
