"""Liquidite, Order Blocks, suivi de zones, Premium/Discount, MTF, analyseur."""

import numpy as np
import pandas as pd
import pytest

from fastlife_quant.data import Timeframe
from fastlife_quant.ict_smc import (
    DealingRange, FibConfig, LiquidityConfig, OrderBlockConfig, StructureConfig, SwingConfig,
    align_htf, analyze, atr, dealing_range_at, detect_liquidity, detect_order_blocks, detect_structure,
    detect_swings, derive_inverse_zones, golden_zone, htf_bias, ote_zone, premium_discount, retracement_zone,
    track_zones,
)
from ict_helpers import SCENARIO, frame, mirror, random_walk, small_cfg


# ---------- liquidite ----------

SWEEP_ROWS = [(10, 11, 9, 10), (10, 13, 10, 12), (12, 12, 10.5, 11), (11, 13.5, 10.5, 12.5)]


def liq(rows, **cfg):
    df = frame(rows)
    return detect_liquidity(df, detect_swings(df, SwingConfig(1, 1)), atr(df, 3), LiquidityConfig(**cfg))


def test_bsl_sweep_wick_and_reclaim():
    res = liq(SWEEP_ROWS)
    sweeps = [e for e in res.events if e.kind == "SWEEP_BSL"]
    assert len(sweeps) == 1
    e = sweeps[0]
    assert (e.detected_idx, e.direction) == (3, "bearish")
    assert e.metrics["level"] == 13.0 and e.metrics["extreme"] == 13.5 and e.metrics["penetration"] == 0.5
    assert e.metrics["bars_to_reclaim"] == 1.0
    lv = next(l for l in res.levels if l.side == "BSL" and l.price == 13.0)
    assert (lv.end_reason, lv.ended_idx) == ("swept", 3)
    assert "re-cloture #3 = 12.5 < 13" in e.explain()


def test_close_above_level_is_break_not_sweep():
    rows = list(SWEEP_ROWS)
    rows[3] = (11, 13.5, 10.5, 13.4)
    res = liq(rows)
    assert not [e for e in res.events if e.kind.startswith("SWEEP")]
    lv = next(l for l in res.levels if l.price == 13.0)
    assert lv.end_reason == "broken"


def test_sweep_with_longer_reclaim_window():
    rows = SWEEP_ROWS[:3] + [(11, 13.5, 10.5, 13.4), (13.4, 13.4, 12, 12.8)]
    assert not [e for e in liq(rows, reclaim_bars=1).events if e.kind.startswith("SWEEP")]
    e = [x for x in liq(rows, reclaim_bars=2).events if x.kind == "SWEEP_BSL"]
    assert len(e) == 1 and e[0].detected_idx == 4 and e[0].metrics["bars_to_reclaim"] == 2.0


def test_ssl_sweep_mirror():
    res = liq(mirror(SWEEP_ROWS))
    e = [x for x in res.events if x.kind == "SWEEP_SSL"]
    assert len(e) == 1 and e[0].direction == "bullish" and e[0].detected_idx == 3


EQUAL_ROWS = [
    (10, 11, 9, 10), (10, 13, 10, 12), (12, 12, 10, 11), (11, 12, 10, 11.5),
    (11.5, 12.95, 11, 12), (12, 12.5, 10.5, 11),
]


def test_equal_highs_detected_within_tolerance():
    res = liq(EQUAL_ROWS)
    eq = [e for e in res.events if e.kind == "EQUAL_HIGHS"]
    assert len(eq) == 1 and eq[0].detected_idx == 5
    assert eq[0].metrics["gap"] == pytest.approx(0.05)
    assert not [e for e in liq(EQUAL_ROWS, equal_tolerance_atr_mult=0.01).events if e.kind == "EQUAL_HIGHS"]


def test_equal_lows_mirror():
    eq = [e for e in liq(mirror(EQUAL_ROWS)).events if e.kind == "EQUAL_LOWS"]
    assert len(eq) == 1


def test_liquidity_prefix_invariance():
    df = frame(EQUAL_ROWS + [(11, 13.5, 10.5, 12.5), (12, 13, 11, 12)])
    cfg = LiquidityConfig()
    sw = detect_swings(df, SwingConfig(1, 1))
    full = detect_liquidity(df, sw, atr(df, 3), cfg)
    for k in range(3, len(df) + 1):
        d = df.iloc[:k]
        part = detect_liquidity(d, detect_swings(d, SwingConfig(1, 1)), atr(d, 3), cfg)
        assert [e.key() for e in part.events] == [e.key() for e in full.events if e.detected_idx < k]


# ---------- order blocks ----------

def obs(rows, cfg, mss=0.5):
    df = frame(rows)
    a = atr(df, 3)
    st = detect_structure(df, detect_swings(df, SwingConfig(1, 1)), a, StructureConfig("close", mss))
    return df, a, detect_order_blocks(df, a, st.events, cfg)


def test_bullish_order_block_confirmed_by_bos():
    _, _, ev = obs(SCENARIO, OrderBlockConfig(displacement_atr_mult=0.8))
    bull = [e for e in ev if e.direction == "bullish"]
    assert len(bull) == 1
    e = bull[0]
    assert e.detected_idx == 5 and e.metrics["ob_idx"] == 3.0
    assert (e.metrics["zone_low"], e.metrics["zone_high"]) == (10.0, 11.0)
    assert "BOS bullish" in " ".join(e.conditions)
    assert "bougie_OB" in {x.label for x in e.evidence}


def test_bearish_order_block_confirmed_by_mss():
    _, _, ev = obs(SCENARIO, OrderBlockConfig(displacement_atr_mult=0.8))
    bear = [e for e in ev if e.direction == "bearish"]
    assert len(bear) == 1 and bear[0].detected_idx == 10 and bear[0].metrics["ob_idx"] == 9.0
    assert (bear[0].metrics["zone_low"], bear[0].metrics["zone_high"]) == (13.8, 14.8)


def test_displacement_threshold_blocks_detection():
    _, _, ev = obs(SCENARIO, OrderBlockConfig(displacement_atr_mult=5.0))
    assert ev == []


def test_confirmation_kind_is_configurable():
    _, _, ev = obs(SCENARIO, OrderBlockConfig(displacement_atr_mult=0.8, accepted_breaks=("MSS",)))
    assert [e.direction for e in ev] == ["bearish"]  # pas de MSS haussier dans le scenario


def test_no_confirmation_required():
    _, _, ev = obs(SCENARIO, OrderBlockConfig(displacement_atr_mult=0.8, require_structure_break=False))
    bull = [e for e in ev if e.direction == "bullish"]
    assert bull and bull[0].detected_idx == 5 and "non exigee" in bull[0].conditions[-2]


def test_multi_bar_displacement():
    _, a, ev = obs(SCENARIO, OrderBlockConfig(displacement_atr_mult=1.4, displacement_bars=2))
    bull = [e for e in ev if e.direction == "bullish"]
    assert len(bull) == 1 and bull[0].metrics["ob_idx"] == 3.0
    assert bull[0].metrics["displacement_atr"] == pytest.approx(3.5 / a[3])


def test_zone_range_mode():
    _, _, ev = obs(SCENARIO, OrderBlockConfig(displacement_atr_mult=0.8, zone="range"))
    bull = next(e for e in ev if e.direction == "bullish")
    assert (bull.metrics["zone_low"], bull.metrics["zone_high"]) == (9.5, 12.0)


def test_order_block_config_validation():
    with pytest.raises(ValueError):
        OrderBlockConfig(zone="x")


# ---------- suivi de zones, IFVG, breaker ----------

def test_tracking_touch_and_breaker():
    rows = SCENARIO + [(11.5, 11.7, 9.0, 9.5)]  # traverse la zone [10, 11] et cloture dessous
    df, a, ev = obs(rows, OrderBlockConfig(displacement_atr_mult=0.8))
    bull = [e for e in ev if e.direction == "bullish"]
    tr = track_zones(df, bull)[0]
    assert (tr.touched_idx, tr.fully_traded_idx, tr.invalidated_idx) == (10, 11, 11)
    inv = derive_inverse_zones(df, [tr])
    assert len(inv) == 1 and (inv[0].kind, inv[0].direction, inv[0].detected_idx) == ("BREAKER", "bearish", 11)
    assert "cloture #11 = 9.5 sous 10" in inv[0].conditions[1]


def test_ifvg_from_invalidated_fvg():
    from fastlife_quant.ict_smc import FVGConfig, detect_fvgs

    rows = [(10, 11, 9, 10), (10, 12, 10, 12), (12, 15, 13, 14), (14, 14, 12, 12.5), (12.5, 12.6, 10, 10.5)]
    df = frame(rows)
    fvg = detect_fvgs(df, atr(df, 2), FVGConfig(0))
    tr = track_zones(df, fvg)[0]  # gap [11, 13]
    assert tr.touched_idx == 3 and tr.invalidated_idx == 4
    ifvg = derive_inverse_zones(df, [tr])[0]
    assert (ifvg.kind, ifvg.direction, ifvg.detected_idx) == ("IFVG", "bearish", 4)


def test_untouched_zone_stays_open():
    df, _, ev = obs(SCENARIO[:6], OrderBlockConfig(displacement_atr_mult=0.8))
    tr = track_zones(df, ev)[0]
    assert (tr.touched_idx, tr.invalidated_idx) == (None, None)


# ---------- premium / discount ----------

def test_premium_discount_zones():
    assert premium_discount(110, 100, 108).zone == "premium"
    assert premium_discount(110, 100, 102).zone == "discount"
    r = premium_discount(110, 100, 105)
    assert r.zone == "equilibrium" and r.position == 0.5 and r.equilibrium == 105
    with pytest.raises(ValueError):
        premium_discount(100, 100, 100)


def test_ote_bullish_and_bearish_leg():
    up = DealingRange(high=110, low=100, high_idx=10, low_idx=0, leg="bullish")
    lo, hi = ote_zone(up, FibConfig())
    assert (lo, hi) == (pytest.approx(102.1), pytest.approx(103.8))  # 110 - 0.79*10 .. 110 - 0.62*10
    down = DealingRange(high=110, low=100, high_idx=0, low_idx=10, leg="bearish")
    lo, hi = ote_zone(down, FibConfig())
    assert (lo, hi) == (pytest.approx(106.2), pytest.approx(107.9))
    g = golden_zone(up, FibConfig())
    assert g == (pytest.approx(103.5), pytest.approx(103.82))
    with pytest.raises(ValueError):
        retracement_zone(100, 110, (0.8, 0.5))


def test_dealing_range_uses_only_confirmed_swings():
    sw = detect_swings(frame(SCENARIO), SwingConfig(1, 1))
    assert dealing_range_at(sw, 2) is None  # un seul swing high confirme, pas de low
    r = dealing_range_at(sw, 4)
    assert (r.high, r.low) == (13.0, 9.5) and r.leg == "bearish"  # le high (#1) precede le low (#3)
    r8 = dealing_range_at(sw, 8)
    assert (r8.high, r8.low, r8.leg) == (14.0, 12.0, "bearish")


# ---------- multi-timeframe ----------

def test_align_htf_uses_only_closed_bars():
    htf = pd.DataFrame({"timestamp": pd.date_range("2026-01-05 00:00", periods=3, freq="1h", tz="UTC"), "v": [1.0, 2.0, 3.0]})
    ltf = pd.DataFrame({"timestamp": pd.date_range("2026-01-05 00:00", periods=12, freq="15min", tz="UTC")})
    out = align_htf(ltf, htf, Timeframe.H1, ["v"]).set_index("timestamp")["htf_v"]
    assert out[pd.Timestamp("2026-01-05 00:45", tz="UTC")] != out[pd.Timestamp("2026-01-05 00:45", tz="UTC")]  # NaN
    assert out[pd.Timestamp("2026-01-05 01:00", tz="UTC")] == 1.0
    assert out[pd.Timestamp("2026-01-05 01:45", tz="UTC")] == 1.0
    assert out[pd.Timestamp("2026-01-05 02:00", tz="UTC")] == 2.0


def test_htf_bias_flips_only_after_htf_close():
    htf = frame(SCENARIO, freq="1h")
    bias = htf_bias(htf, Timeframe.H1, small_cfg())
    assert list(bias["bias"][[4, 5, 9, 10]]) == ["neutral", "bullish", "bullish", "bearish"]
    ltf = pd.DataFrame({"timestamp": pd.date_range("2026-01-05 00:00", periods=12 * 12, freq="5min", tz="UTC")})
    out = align_htf(ltf, bias, Timeframe.H1, ["bias"]).set_index("timestamp")["htf_bias"]
    assert out[pd.Timestamp("2026-01-05 10:55", tz="UTC")] == "bullish"  # bougie HTF #10 pas encore close
    assert out[pd.Timestamp("2026-01-05 11:00", tz="UTC")] == "bearish"


def test_align_requires_sorted_input():
    htf = pd.DataFrame({"timestamp": pd.date_range("2026-01-05", periods=2, freq="1h", tz="UTC")[::-1], "v": [1.0, 2.0]})
    ltf = pd.DataFrame({"timestamp": pd.date_range("2026-01-05", periods=2, freq="15min", tz="UTC")})
    with pytest.raises(ValueError):
        align_htf(ltf, htf, Timeframe.H1, ["v"])


# ---------- analyseur ----------

def test_analyze_rejects_invalid_series():
    df = frame(SCENARIO)
    bad = pd.concat([df, df.iloc[[3]]]).sort_values("timestamp", kind="stable")
    with pytest.raises(ValueError, match="duplicate_timestamps"):
        analyze(bad, Timeframe.M5, small_cfg())


def test_analyze_scenario_end_to_end():
    res = analyze(frame(SCENARIO), Timeframe.M5, small_cfg(order_block=OrderBlockConfig(displacement_atr_mult=0.8)))
    kinds_ = {e.kind for e in res.all_events()}
    assert {"BOS", "CHOCH", "MSS", "ORDER_BLOCK"} <= kinds_
    assert all(e.explain() for e in res.all_events())


def test_analyzer_prefix_invariance_on_random_walk():
    """Aucun look-ahead : analyser les k premieres bougies donne les memes evenements."""
    df = random_walk(400)
    cfg = small_cfg(swing=SwingConfig(2, 2), external_swing=SwingConfig(5, 5), atr=__import__("fastlife_quant.ict_smc", fromlist=["ATRConfig"]).ATRConfig(14),
                    order_block=OrderBlockConfig(displacement_atr_mult=1.0))
    full = analyze(df, Timeframe.M5, cfg)
    all_full = full.all_events()
    assert len(all_full) > 20  # le test est significatif
    kinds_seen = {e.kind for e in all_full}
    assert {"BOS", "FVG", "ORDER_BLOCK"} <= kinds_seen
    for k in (60, 150, 299):
        part = analyze(df.iloc[:k], Timeframe.M5, cfg)
        assert [e.key() for e in part.all_events()] == [e.key() for e in all_full if e.detected_idx < k]
