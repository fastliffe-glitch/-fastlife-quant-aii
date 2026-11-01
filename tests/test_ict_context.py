"""Tests for ict_smc/context.py: premium, discount, equilibrium, OTE, multi-timeframe.

These tests exercise the behaviour of the original implementation (config
thresholds premium_threshold=0.6, discount_threshold=0.4, ote_level=0.618).
They use separate, hand-built frames per zone: premium, discount and
equilibrium are mutually exclusive by construction, so a single bar can never
trigger all of them.

All frames are synthetic test data.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fastlife_quant.ict_smc import (
    detect_discount,
    detect_equilibrium,
    detect_ote,
    detect_premium,
    multi_timeframe_analysis,
)
from fastlife_quant.ict_smc.config import ICTSMCConfig
from fastlife_quant.ict_smc.engine import ICTSMCEngine


def make_frame(rows, timeframe="M5"):
    """rows: iterable of (open, high, low, close)."""
    rows = list(rows)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-05 00:00", periods=len(rows), freq="5min", tz="UTC"),
            "open": [r[0] for r in rows],
            "high": [r[1] for r in rows],
            "low": [r[2] for r in rows],
            "close": [r[3] for r in rows],
            "timeframe": [timeframe] * len(rows),
        }
    )


# Every frame below spans low = 8 .. high = 18 (range 10) over its 5 bars; the
# interesting bar is the last one (idx 4).
#   position in range = (close - 8) / 10
PREMIUM_ROWS = [
    (9, 10, 8, 9),
    (10, 12, 9, 11),
    (12, 14, 11, 13),
    (14, 16, 13, 15),
    (16, 18, 15, 17.5),  # close at 95 % of the range
]
DISCOUNT_ROWS = [
    (17, 18, 16, 17),
    (15, 16, 13, 14),
    (13, 14, 11, 12),
    (11, 12, 9, 10),
    (9, 10.5, 8, 8.5),  # close at 5 % of the range
]
EQUILIBRIUM_ROWS = [
    (9, 12, 8, 10),
    (11, 18, 11, 17),
    (16, 17, 12, 14),
    (14, 15, 12.5, 13.5),
    (13.5, 14, 12.5, 13.2),  # close at 52 %, mid is 13.0
]
# Same as the equilibrium frame but the last bar trades through the 61.8 %
# level (8 + 10 * 0.618 = 14.18).
OTE_ROWS = EQUILIBRIUM_ROWS[:-1] + [(13.5, 15, 12.5, 13.5)]

LAST = 4


# --------------------------------------------------------------------------- #
# Premium / discount / equilibrium zones
# --------------------------------------------------------------------------- #


def test_premium_zone_fires_only_premium():
    df = make_frame(PREMIUM_ROWS)

    event = detect_premium(df, LAST)

    assert event is not None
    assert event.event_type == "premium"
    assert event.price == pytest.approx(17.5)
    assert detect_discount(df, LAST) is None
    assert detect_equilibrium(df, LAST) is None


def test_discount_zone_fires_only_discount():
    df = make_frame(DISCOUNT_ROWS)

    event = detect_discount(df, LAST)

    assert event is not None
    assert event.event_type == "discount"
    assert event.price == pytest.approx(8.5)
    assert detect_premium(df, LAST) is None
    assert detect_equilibrium(df, LAST) is None


def test_equilibrium_zone_fires_only_equilibrium():
    df = make_frame(EQUILIBRIUM_ROWS)

    event = detect_equilibrium(df, LAST)

    assert event is not None
    assert event.event_type == "equilibrium"
    assert event.price == pytest.approx(13.0)  # midpoint of 8..18
    assert detect_premium(df, LAST) is None
    assert detect_discount(df, LAST) is None


def test_premium_threshold_is_strict():
    # position = (14.0 - 8) / 10 = 0.6, exactly the threshold: not premium.
    at_threshold = make_frame(PREMIUM_ROWS[:-1] + [(13, 18, 8, 14.0)])
    just_above = make_frame(PREMIUM_ROWS[:-1] + [(13, 18, 8, 14.01)])

    assert detect_premium(at_threshold, LAST) is None
    assert detect_premium(just_above, LAST) is not None


def test_zones_follow_config_thresholds():
    df = make_frame(EQUILIBRIUM_ROWS)  # position 0.52

    assert detect_premium(df, LAST) is None
    assert detect_premium(df, LAST, ICTSMCConfig(premium_threshold=0.5)) is not None

    assert detect_discount(df, LAST) is None
    # discount fires when position < discount_threshold; 0.52 < 0.55
    assert detect_discount(df, LAST, ICTSMCConfig(discount_threshold=0.55)) is not None


def test_flat_market_has_no_premium_or_discount():
    df = make_frame([(10, 10, 10, 10)] * 5)

    assert detect_premium(df, LAST) is None
    assert detect_discount(df, LAST) is None


@pytest.mark.parametrize("detector", [detect_premium, detect_discount, detect_equilibrium, detect_ote])
def test_zone_detectors_need_at_least_two_bars(detector):
    df = make_frame(PREMIUM_ROWS)

    assert detector(df, 0) is None


# --------------------------------------------------------------------------- #
# OTE
# --------------------------------------------------------------------------- #


def test_ote_fires_when_the_bar_trades_through_the_618_level():
    df = make_frame(OTE_ROWS)

    event = detect_ote(df, LAST)

    assert event is not None
    assert event.event_type == "ote"
    assert event.price == pytest.approx(8 + 10 * 0.618)


def test_ote_does_not_fire_when_the_bar_stays_away_from_the_level():
    # last bar of the premium frame is 15..18 with a close at 17.5: the 14.18
    # level lies below the whole bar.
    assert detect_ote(make_frame(PREMIUM_ROWS), LAST) is None
    # last bar of the equilibrium frame is 12.5..14: it never reaches 14.18.
    assert detect_ote(make_frame(EQUILIBRIUM_ROWS), LAST) is None


def test_ote_level_comes_from_config():
    df = make_frame(EQUILIBRIUM_ROWS)  # last bar 12.5..14, close 13.2

    event = detect_ote(df, LAST, ICTSMCConfig(ote_level=0.5))  # level = 13.0

    assert event is not None
    assert event.price == pytest.approx(13.0)


# --------------------------------------------------------------------------- #
# No look-ahead: a decision at bar idx must not depend on later bars
# --------------------------------------------------------------------------- #

FUTURE_BARS = [(500, 1000, 1, 2), (3, 900, 2, 800), (700, 950, 5, 6)]


@pytest.mark.parametrize(
    "detector, rows",
    [
        (detect_premium, PREMIUM_ROWS),
        (detect_discount, DISCOUNT_ROWS),
        (detect_equilibrium, EQUILIBRIUM_ROWS),
        (detect_ote, OTE_ROWS),
    ],
)
def test_context_detectors_do_not_look_ahead(detector, rows):
    prefix = make_frame(rows)
    extended = make_frame(rows + FUTURE_BARS)

    on_prefix = detector(prefix, LAST)
    on_extended = detector(extended, LAST)

    assert on_prefix is not None  # guard: a None == None comparison proves nothing
    assert on_extended is not None
    assert on_extended.as_dict() == on_prefix.as_dict()


# --------------------------------------------------------------------------- #
# Multi-timeframe summary
# --------------------------------------------------------------------------- #


def test_multi_timeframe_analysis_summarises_each_timeframe():
    rising = make_frame([(100, 101, 99, 100), (100, 103, 99, 102), (102, 106, 101, 105)], "M5")
    falling = make_frame([(105, 106, 104, 105), (105, 105, 101, 102), (102, 103, 99, 100)], "H1")

    summary = multi_timeframe_analysis({"M5": rising, "H1": falling})

    assert set(summary) == {"M5", "H1"}
    assert summary["M5"] == {"last_close": 105.0, "last_high": 106.0, "last_low": 101.0, "trend": "bullish"}
    assert summary["H1"] == {"last_close": 100.0, "last_high": 103.0, "last_low": 99.0, "trend": "bearish"}


def test_multi_timeframe_analysis_skips_empty_frames():
    rising = make_frame([(100, 101, 99, 100), (100, 103, 99, 102)], "M5")
    empty = make_frame([], "H4")

    summary = multi_timeframe_analysis({"M5": rising, "H4": empty})

    assert set(summary) == {"M5"}


# --------------------------------------------------------------------------- #
# Engine integration
# --------------------------------------------------------------------------- #


def test_engine_emits_context_events_from_the_restored_detectors():
    events = ICTSMCEngine().analyze(make_frame(PREMIUM_ROWS), timeframe="M5")

    emitted = {(e["event_type"], e["timestamp"]) for e in events}
    last_ts = make_frame(PREMIUM_ROWS)["timestamp"].iloc[LAST]

    assert ("premium", last_ts) in emitted
