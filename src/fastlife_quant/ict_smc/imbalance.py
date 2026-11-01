from __future__ import annotations

from typing import Any

import pandas as pd

from fastlife_quant.ict_smc.config import ICTSMCConfig
from fastlife_quant.ict_smc.events import ICTEvent


def detect_bsl(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    if float(current["close"]) > float(prev["close"]) and current["high"] >= prev["high"]:
        return ICTEvent(
            event_type="bsl",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["high"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("buy_side_liquidity_above_prev_high",),
            parameters={"atr_period": config.atr_period},
            confirmed=True,
            invalidation_level=float(prev["high"]),
        )
    return None


def detect_ssl(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    if float(current["close"]) < float(prev["close"]) and current["low"] <= prev["low"]:
        return ICTEvent(
            event_type="ssl",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["low"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("sell_side_liquidity_below_prev_low",),
            parameters={"atr_period": config.atr_period},
            confirmed=True,
            invalidation_level=float(prev["low"]),
        )
    return None


def detect_equal_highs(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    if idx < 1:
        return None
    prev = df.iloc[idx - 1]
    current = df.iloc[idx]
    if abs(float(current["high"]) - float(prev["high"])) <= 1e-9:
        return ICTEvent(
            event_type="equal_highs",
            direction="neutral",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["high"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("equal_highs",),
            parameters={"tolerance": 1e-9},
            confirmed=True,
            invalidation_level=float(current["high"]),
        )
    return None


def detect_equal_lows(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    if idx < 1:
        return None
    prev = df.iloc[idx - 1]
    current = df.iloc[idx]
    if abs(float(current["low"]) - float(prev["low"])) <= 1e-9:
        return ICTEvent(
            event_type="equal_lows",
            direction="neutral",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["low"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("equal_lows",),
            parameters={"tolerance": 1e-9},
            confirmed=True,
            invalidation_level=float(current["low"]),
        )
    return None


def detect_liquidity_sweep(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    if float(current["low"]) < float(prev["low"]) and float(current["close"]) > float(prev["close"]):
        return ICTEvent(
            event_type="liquidity_sweep",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["low"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("sweeps_prior_low", "reclaims_from_below"),
            parameters={"atr_period": config.atr_period},
            confirmed=True,
            invalidation_level=float(prev["low"]),
        )
    if float(current["high"]) > float(prev["high"]) and float(current["close"]) < float(prev["close"]):
        return ICTEvent(
            event_type="liquidity_sweep",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["high"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("sweeps_prior_high", "reclaims_from_above"),
            parameters={"atr_period": config.atr_period},
            confirmed=True,
            invalidation_level=float(prev["high"]),
        )
    return None


def detect_inducement(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    if idx < 1:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    if float(current["close"]) > float(prev["close"]) and float(current["low"]) <= float(prev["low"]):
        return ICTEvent(
            event_type="inducement",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["low"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("inducement_bullish", "draws_below_prior_low"),
            parameters={},
            confirmed=True,
            invalidation_level=float(prev["low"]),
        )
    if float(current["close"]) < float(prev["close"]) and float(current["high"]) >= float(prev["high"]):
        return ICTEvent(
            event_type="inducement",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["high"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("inducement_bearish", "draws_above_prior_high"),
            parameters={},
            confirmed=True,
            invalidation_level=float(prev["high"]),
        )
    return None


__all__ = [
    "detect_bsl",
    "detect_ssl",
    "detect_equal_highs",
    "detect_equal_lows",
    "detect_liquidity_sweep",
    "detect_inducement",
]
