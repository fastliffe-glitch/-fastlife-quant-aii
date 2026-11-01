from __future__ import annotations

import pandas as pd

from fastlife_quant.ict_smc.atr import compute_atr
from fastlife_quant.ict_smc.config import ICTSMCConfig
from fastlife_quant.ict_smc.events import ICTEvent


def detect_bullish_fvg(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2 or idx >= len(df):
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    prev2 = df.iloc[idx - 2]
    atr = compute_atr(df.iloc[: idx + 1], period=config.atr_period).iloc[-1]
    bull = float(current["low"]) > float(prev2["high"]) and float(current["close"]) > float(current["open"])
    if not bull:
        return None
    if config.fvg_atr_filter and atr and float(current["low"]) - float(prev2["high"]) < atr * config.fvg_atr_filter:
        return None
    return ICTEvent(
        event_type="bullish_fvg",
        direction="bullish",
        timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
        timestamp=current["timestamp"],
        price=float(current["low"]),
        reference_bars=[prev2["timestamp"], prev["timestamp"], current["timestamp"]],
        trigger_conditions=("bullish_gap", "low_above_prior_high"),
        parameters={"atr_period": config.atr_period, "fvg_atr_filter": config.fvg_atr_filter},
        confirmed=True,
        invalidation_level=float(prev2["high"]),
        metadata={"fvg_size": float(current["low"]) - float(prev2["high"])},
    )


def detect_bearish_fvg(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2 or idx >= len(df):
        return None
    current = df.iloc[idx]
    prev2 = df.iloc[idx - 2]
    atr = compute_atr(df.iloc[: idx + 1], period=config.atr_period).iloc[-1]
    bear = float(current["high"]) < float(prev2["low"]) and float(current["close"]) < float(current["open"])
    if not bear:
        return None
    if config.fvg_atr_filter and atr and float(prev2["low"]) - float(current["high"]) < atr * config.fvg_atr_filter:
        return None
    return ICTEvent(
        event_type="bearish_fvg",
        direction="bearish",
        timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
        timestamp=current["timestamp"],
        price=float(current["high"]),
        reference_bars=[df["timestamp"].iloc[idx - 2], df["timestamp"].iloc[idx - 1], current["timestamp"]],
        trigger_conditions=("bearish_gap", "high_below_prior_low"),
        parameters={"atr_period": config.atr_period, "fvg_atr_filter": config.fvg_atr_filter},
        confirmed=True,
        invalidation_level=float(prev2["low"]),
        metadata={"fvg_size": float(prev2["low"]) - float(current["high"])},
    )


def detect_inverse_fvg(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2:
        return None
    current = df.iloc[idx]
    prev2 = df.iloc[idx - 2]
    if float(current["high"]) < float(prev2["high"]) and float(current["low"]) > float(prev2["low"]):
        return ICTEvent(
            event_type="inverse_fvg",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev2["timestamp"], df["timestamp"].iloc[idx - 1], current["timestamp"]],
            trigger_conditions=("inverse_gap", "consolidation_inside_prior_range"),
            parameters={"atr_period": config.atr_period},
            confirmed=True,
            invalidation_level=float(prev2["low"]),
        )
    return None


def detect_displacement(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 1:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    atr = compute_atr(df.iloc[: idx + 1], period=config.atr_period).iloc[-1]
    if atr == 0:
        return None
    if float(current["close"]) - float(prev["close"]) >= atr * config.min_displacement_atr:
        return ICTEvent(
            event_type="displacement",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("significant_up_move", "measured_by_atr"),
            parameters={"atr_period": config.atr_period, "min_displacement_atr": config.min_displacement_atr},
            confirmed=True,
            invalidation_level=float(prev["close"]),
        )
    if float(prev["close"]) - float(current["close"]) >= atr * config.min_displacement_atr:
        return ICTEvent(
            event_type="displacement",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("significant_down_move", "measured_by_atr"),
            parameters={"atr_period": config.atr_period, "min_displacement_atr": config.min_displacement_atr},
            confirmed=True,
            invalidation_level=float(prev["close"]),
        )
    return None


__all__ = [
    "detect_bullish_fvg",
    "detect_bearish_fvg",
    "detect_inverse_fvg",
    "detect_displacement",
]
