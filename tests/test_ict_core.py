"""ATR, swings, FVG, structure (BOS/CHoCH/MSS)."""

import numpy as np
import pytest

from fastlife_quant.ict_smc import (
    FVGConfig, StructureConfig, SwingConfig, atr, detect_fvgs, detect_structure, detect_swings, swings_known_at,
)
from ict_helpers import SCENARIO, frame, mirror


# ---------- ATR ----------

def test_atr_constant_range_and_nan_warmup():
    df = frame([(10, 12, 10, 11)] * 6)  # range 2, pas de gap
    a = atr(df, 3)
    assert np.isnan(a[:2]).all()
    assert a[2:] == pytest.approx(2.0)


def test_atr_is_causal():
    df = frame(SCENARIO)
    full = atr(df, 3)
    for k in (5, 8):
        np.testing.assert_allclose(atr(df.iloc[:k], 3), full[:k], equal_nan=True)


# ---------- swings ----------

def test_swing_high_confirmed_after_right_bars():
    rows = [(5, 5, 4, 4.5), (6, 6, 5, 5.5), (7, 7, 6, 6.5), (9, 10, 9, 9.5), (7, 7, 6, 6.5), (6, 6, 5, 5.5), (5, 5, 4, 4.5)]
    sw = detect_swings(frame(rows), SwingConfig(3, 3))
    highs = [s for s in sw if s.kind == "high"]
    assert [(s.idx, s.price, s.confirmed_idx) for s in highs] == [(3, 10.0, 6)]
    assert not [s for s in sw if s.kind == "low"]


def test_swing_low_mirror():
    rows = [(5, 5, 4, 4.5), (6, 6, 5, 5.5), (7, 7, 6, 6.5), (9, 10, 9, 9.5), (7, 7, 6, 6.5), (6, 6, 5, 5.5), (5, 5, 4, 4.5)]
    sw = detect_swings(frame(mirror(rows)), SwingConfig(3, 3))
    lows = [s for s in sw if s.kind == "low"]
    assert [(s.idx, s.price, s.confirmed_idx) for s in lows] == [(3, 30.0, 6)]


def test_equal_highs_first_is_the_swing():
    rows = [(1, 1, 0, 0.5), (2, 2, 1, 1.5), (5, 9, 4, 8), (8, 9, 7, 8), (2, 2, 1, 1.5), (1, 1, 0, 0.5)]
    highs = [s for s in detect_swings(frame(rows), SwingConfig(2, 2)) if s.kind == "high"]
    assert [s.idx for s in highs] == [2]


def test_swings_known_at_respects_confirmation_delay():
    sw = detect_swings(frame(SCENARIO), SwingConfig(1, 1))
    sh = next(s for s in sw if s.kind == "high" and s.idx == 1)
    assert sh.confirmed_idx == 2
    assert sh not in swings_known_at(sw, 1)
    assert sh in swings_known_at(sw, 2)


def test_swing_config_validation():
    with pytest.raises(ValueError):
        SwingConfig(0, 3)


def test_swings_prefix_invariance():
    df = frame(SCENARIO)
    full = detect_swings(df, SwingConfig(1, 1))
    for k in range(3, len(df)):
        part = detect_swings(df.iloc[:k], SwingConfig(1, 1))
        assert [(s.kind, s.idx, s.confirmed_idx) for s in part] == [
            (s.kind, s.idx, s.confirmed_idx) for s in full if s.confirmed_idx < k
        ]


# ---------- FVG ----------

FVG_BULL = [(10, 11, 9, 10), (10, 12, 10, 12), (12, 15, 13, 14)]  # low3=13 > high1=11 -> gap [11,13]
FVG_BEAR = [(20, 21, 19, 20), (20, 20, 17, 17), (17, 16, 14, 15)]  # high3=16 < low1=19 -> gap [16,19]


def test_bullish_fvg_geometry_and_size():
    df = frame(FVG_BULL)
    ev = detect_fvgs(df, atr(df, 2), FVGConfig(0))
    assert len(ev) == 1
    e = ev[0]
    assert (e.kind, e.direction, e.detected_idx) == ("FVG", "bullish", 2)
    assert (e.metrics["zone_low"], e.metrics["zone_high"], e.metrics["size"]) == (11.0, 13.0, 2.0)
    assert [x.idx for x in e.evidence] == [0, 1, 2]
    assert "low #2 = 13 > high #0 = 11" in e.conditions[0]


def test_bearish_fvg():
    df = frame(FVG_BEAR)
    e = detect_fvgs(df, atr(df, 2), FVGConfig(0))[0]
    assert e.direction == "bearish"
    assert (e.metrics["zone_low"], e.metrics["zone_high"], e.metrics["size"]) == (16.0, 19.0, 3.0)


def test_no_fvg_when_candles_overlap():
    df = frame([(10, 11, 9, 10), (10, 12, 10, 11), (11, 12, 10.5, 11.5)])
    assert detect_fvgs(df, atr(df, 2), FVGConfig(0)) == []


def test_fvg_atr_filter():
    df = frame(FVG_BULL + [(14, 15, 13, 14)])
    a = atr(df, 2)
    small = detect_fvgs(df, a, FVGConfig(0.1))
    assert len(small) == 1 and "size_atr" in small[0].metrics
    ref = a[1]
    huge = FVGConfig(min_atr_mult=2.0 / ref + 0.5)  # gap=2 < mult*ATR
    assert detect_fvgs(df, a, huge) == []


def test_fvg_filter_requires_atr():
    df = frame(FVG_BULL)
    a = atr(df, 14)  # tout NaN
    assert detect_fvgs(df, a, FVGConfig(0.1)) == []
    assert len(detect_fvgs(df, a, FVGConfig(0))) == 1


def test_fvg_uses_only_past_bars():
    df = frame(FVG_BULL + [(14, 15, 13, 14), (14, 16, 13, 15)])
    a = atr(df, 2)
    full = detect_fvgs(df, a, FVGConfig(0))
    for k in range(3, len(df) + 1):
        part = detect_fvgs(df.iloc[:k], atr(df.iloc[:k], 2), FVGConfig(0))
        assert [e.key() for e in part] == [e.key() for e in full if e.detected_idx < k]


# ---------- structure ----------

def structure(rows, mss_mult=0.5, break_on="close"):
    df = frame(rows)
    sw = detect_swings(df, SwingConfig(1, 1))
    return detect_structure(df, sw, atr(df, 3), StructureConfig(break_on, mss_mult))


def kinds(res):
    return [(e.kind, e.direction, e.detected_idx) for e in res.events]


def test_bos_choch_mss_sequence():
    res = structure(SCENARIO)
    assert kinds(res) == [
        ("BOS", "bullish", 5),
        ("BOS", "bullish", 9),
        ("CHOCH", "bearish", 10),
        ("MSS", "bearish", 10),
    ]
    assert res.events[0].metrics["initial"] == 1.0 and res.events[1].metrics["initial"] == 0.0
    assert list(res.trend[[4, 5, 9, 10]]) == [0, 1, 1, -1]


def test_mss_requires_displacement():
    res = structure(SCENARIO, mss_mult=50)
    assert [k[0] for k in kinds(res)] == ["BOS", "BOS", "CHOCH"]


def test_structure_mirror_is_symmetric():
    res = structure(mirror(SCENARIO))
    assert kinds(res) == [
        ("BOS", "bearish", 5),
        ("BOS", "bearish", 9),
        ("CHOCH", "bullish", 10),
        ("MSS", "bullish", 10),
    ]


def test_wick_vs_close_break():
    rows = list(SCENARIO)
    rows[5] = (11.5, 14, 11, 12.9)  # meche au-dessus de 13, cloture dessous
    assert kinds(structure(rows))[0] == ("BOS", "bullish", 9)
    assert kinds(structure(rows, break_on="wick"))[0] == ("BOS", "bullish", 5)


def test_structure_event_is_explainable():
    e = structure(SCENARIO).events[2]
    text = e.explain()
    assert "CHOCH bearish" in text and "bougie_de_cassure" in text and "swing_casse" in text
    assert "11.5 < 12" in text
    assert {x.label for x in e.evidence} == {"swing_casse", "bougie_de_cassure"}


def test_structure_prefix_invariance():
    df = frame(SCENARIO)
    sw_all = detect_swings(df, SwingConfig(1, 1))
    full = detect_structure(df, sw_all, atr(df, 3), StructureConfig("close", 0.5))
    for k in range(2, len(df) + 1):
        d = df.iloc[:k]
        part = detect_structure(d, detect_swings(d, SwingConfig(1, 1)), atr(d, 3), StructureConfig("close", 0.5))
        assert [e.key() for e in part.events] == [e.key() for e in full.events if e.detected_idx < k]
