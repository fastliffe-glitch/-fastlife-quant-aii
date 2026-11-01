from __future__ import annotations

from typing import Any

import pandas as pd

from fastlife_quant.ict_smc.config import ICTSMCConfig
from fastlife_quant.ict_smc.events import ICTEvent


def _reference_bars(df: pd.DataFrame, start: int, end: int) -> list[pd.Timestamp]:
    return [ts for ts in df["timestamp"].iloc[start : end + 1].tolist()]


def detect_swing_high(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < config.swing_left_bars or idx >= len(df):
        return None
    current = df.iloc[idx]
    left = df.iloc[max(0, idx - config.swing_left_bars) : idx + 1]
    if float(current["high"]) < float(left["high"].max()):
        return None
    confirmed = idx + config.swing_right_bars < len(df)
    return ICTEvent(
        event_type="swing_high",
        direction="bullish",
        timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
        timestamp=current["timestamp"],
        price=float(current["high"]),
        reference_bars=_reference_bars(df, max(0, idx - config.swing_left_bars), idx),
        trigger_conditions=("local_high", "left_context", "confirmation_closed" if confirmed else "pending_confirmation"),
        parameters={"left_bars": config.swing_left_bars, "right_bars": config.swing_right_bars},
        confirmed=confirmed,
        invalidation_level=float(current["high"]),
    )


def detect_swing_low(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < config.swing_left_bars or idx >= len(df):
        return None
    current = df.iloc[idx]
    left = df.iloc[max(0, idx - config.swing_left_bars) : idx + 1]
    if float(current["low"]) > float(left["low"].min()):
        return None
    confirmed = idx + config.swing_right_bars < len(df)
    return ICTEvent(
        event_type="swing_low",
        direction="bearish",
        timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
        timestamp=current["timestamp"],
        price=float(current["low"]),
        reference_bars=_reference_bars(df, max(0, idx - config.swing_left_bars), idx),
        trigger_conditions=("local_low", "left_context", "confirmation_closed" if confirmed else "pending_confirmation"),
        parameters={"left_bars": config.swing_left_bars, "right_bars": config.swing_right_bars},
        confirmed=confirmed,
        invalidation_level=float(current["low"]),
    )


def detect_bos(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2 or idx >= len(df):
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    prev2 = df.iloc[idx - 2]
    if float(current["close"]) > float(prev["close"]) and float(prev["close"]) > float(prev2["close"]):
        return ICTEvent(
            event_type="bos",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev2["timestamp"], prev["timestamp"], current["timestamp"]],
            trigger_conditions=("sequence_up",),
            parameters={"structural_confirmation_bars": config.structural_confirmation_bars},
            confirmed=idx >= config.structural_confirmation_bars,
            invalidation_level=float(prev["close"]),
        )
    if float(current["close"]) < float(prev["close"]) and float(prev["close"]) < float(prev2["close"]):
        return ICTEvent(
            event_type="bos",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev2["timestamp"], prev["timestamp"], current["timestamp"]],
            trigger_conditions=("sequence_down",),
            parameters={"structural_confirmation_bars": config.structural_confirmation_bars},
            confirmed=idx >= config.structural_confirmation_bars,
            invalidation_level=float(prev["close"]),
        )
    return None


def detect_choch(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2 or idx >= len(df):
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    prev2 = df.iloc[idx - 2]
    if float(current["close"]) > float(prev["close"]) and float(prev["close"]) < float(prev2["close"]):
        return ICTEvent(
            event_type="choch",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev2["timestamp"], prev["timestamp"], current["timestamp"]],
            trigger_conditions=("trend_change_up",),
            parameters={"structural_confirmation_bars": config.structural_confirmation_bars},
            confirmed=idx >= config.structural_confirmation_bars,
            invalidation_level=float(prev["low"]),
        )
    if float(current["close"]) < float(prev["close"]) and float(prev["close"]) > float(prev2["close"]):
        return ICTEvent(
            event_type="choch",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev2["timestamp"], prev["timestamp"], current["timestamp"]],
            trigger_conditions=("trend_change_down",),
            parameters={"structural_confirmation_bars": config.structural_confirmation_bars},
            confirmed=idx >= config.structural_confirmation_bars,
            invalidation_level=float(prev["high"]),
        )
    return None


def detect_mss(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 4 or idx >= len(df):
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    prev2 = df.iloc[idx - 2]
    prior_window = df.iloc[max(0, idx - 4) : idx]
    if float(current["close"]) > float(prev["close"]) > float(prev2["close"]) and float(current["close"]) > float(prior_window["close"].max()):
        return ICTEvent(
            event_type="mss",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prior_window["timestamp"].iloc[0], prev["timestamp"], current["timestamp"]],
            trigger_conditions=("momentum_shift_bullish",),
            parameters={"structural_confirmation_bars": config.structural_confirmation_bars},
            confirmed=idx >= config.structural_confirmation_bars,
            invalidation_level=float(prev["low"]),
        )
    if float(current["close"]) < float(prev["close"]) < float(prev2["close"]) and float(current["close"]) < float(prior_window["close"].min()):
        return ICTEvent(
            event_type="mss",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prior_window["timestamp"].iloc[0], prev["timestamp"], current["timestamp"]],
            trigger_conditions=("momentum_shift_bearish",),
            parameters={"structural_confirmation_bars": config.structural_confirmation_bars},
            confirmed=idx >= config.structural_confirmation_bars,
            invalidation_level=float(prev["high"]),
        )
    return None


def detect_internal_structure(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    if idx < 1:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    if float(current["high"]) > float(prev["high"]) and float(current["low"]) > float(prev["low"]):
        return ICTEvent(
            event_type="internal_structure",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("higher_high", "higher_low"),
            parameters={"confirmation_only_closed": bool((config or ICTSMCConfig()).confirmation_only_closed)},
            confirmed=True,
            invalidation_level=float(prev["low"]),
        )
    if float(current["high"]) < float(prev["high"]) and float(current["low"]) < float(prev["low"]):
        return ICTEvent(
            event_type="internal_structure",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("lower_high", "lower_low"),
            parameters={"confirmation_only_closed": bool((config or ICTSMCConfig()).confirmation_only_closed)},
            confirmed=True,
            invalidation_level=float(prev["high"]),
        )
    return None


def detect_external_structure(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    if idx < 1:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    if float(current["high"]) > float(prev["high"]) and float(current["low"]) < float(prev["low"]):
        return ICTEvent(
            event_type="external_structure",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("higher_high", "lower_low"),
            parameters={"confirmation_only_closed": bool((config or ICTSMCConfig()).confirmation_only_closed)},
            confirmed=True,
            invalidation_level=float(prev["close"]),
        )
    if float(current["high"]) < float(prev["high"]) and float(current["low"]) > float(prev["low"]):
        return ICTEvent(
            event_type="external_structure",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("lower_high", "higher_low"),
            parameters={"confirmation_only_closed": bool((config or ICTSMCConfig()).confirmation_only_closed)},
            confirmed=True,
            invalidation_level=float(prev["close"]),
        )
    return None


__all__ = [
    "detect_swing_high",
    "detect_swing_low",
    "detect_bos",
    "detect_choch",
    "detect_mss",
    "detect_internal_structure",
    "detect_external_structure",
]
