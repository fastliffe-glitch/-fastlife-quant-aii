from __future__ import annotations

import pandas as pd

from fastlife_quant.ict_smc.atr import compute_atr
from fastlife_quant.ict_smc.config import ICTSMCConfig
from fastlife_quant.ict_smc.events import ICTEvent


def detect_bullish_order_block(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    atr = compute_atr(df.iloc[: idx + 1], period=config.atr_period).iloc[-1]
    if atr == 0:
        return None
    # derniere bougie baissiere avant un deplacement haussier significatif
    bearish_prev = df.iloc[:idx].tail(10)
    if bearish_prev.empty:
        return None
    last_bearish = bearish_prev.loc[bearish_prev["close"] == bearish_prev["close"].min()].iloc[-1]
    if float(current["close"]) - float(last_bearish["close"]) >= atr * config.order_block_atr_threshold:
        return ICTEvent(
            event_type="bullish_order_block",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(last_bearish["close"]),
            reference_bars=[last_bearish["timestamp"], current["timestamp"]],
            trigger_conditions=("last_opposite_candle_before_move", "displacement_above_atr_threshold"),
            parameters={"atr_period": config.atr_period, "order_block_atr_threshold": config.order_block_atr_threshold},
            confirmed=True,
            invalidation_level=float(last_bearish["close"]),
        )
    return None


def detect_bearish_order_block(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 2:
        return None
    current = df.iloc[idx]
    atr = compute_atr(df.iloc[: idx + 1], period=config.atr_period).iloc[-1]
    if atr == 0:
        return None
    bullish_prev = df.iloc[:idx].tail(10)
    if bullish_prev.empty:
        return None
    last_bullish = bullish_prev.loc[bullish_prev["close"] == bullish_prev["close"].max()].iloc[-1]
    if float(last_bullish["close"]) - float(current["close"]) >= atr * config.order_block_atr_threshold:
        return ICTEvent(
            event_type="bearish_order_block",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(last_bullish["close"]),
            reference_bars=[last_bullish["timestamp"], current["timestamp"]],
            trigger_conditions=("last_opposite_candle_before_move", "displacement_below_atr_threshold"),
            parameters={"atr_period": config.atr_period, "order_block_atr_threshold": config.order_block_atr_threshold},
            confirmed=True,
            invalidation_level=float(last_bullish["close"]),
        )
    return None


def detect_mitigation(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    if idx < 1:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    if float(current["close"]) >= float(prev["close"]) and float(current["low"]) <= float(prev["low"]):
        return ICTEvent(
            event_type="mitigation",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["low"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("mitigation_bullish",),
            parameters={},
            confirmed=True,
            invalidation_level=float(prev["low"]),
        )
    if float(current["close"]) <= float(prev["close"]) and float(current["high"]) >= float(prev["high"]):
        return ICTEvent(
            event_type="mitigation",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["high"]),
            reference_bars=[prev["timestamp"], current["timestamp"]],
            trigger_conditions=("mitigation_bearish",),
            parameters={},
            confirmed=True,
            invalidation_level=float(prev["high"]),
        )
    return None


def detect_breaker_block(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 3:
        return None
    current = df.iloc[idx]
    prev = df.iloc[idx - 1]
    prev2 = df.iloc[idx - 2]
    if float(current["close"]) > float(prev["close"]) > float(prev2["close"]):
        return ICTEvent(
            event_type="breaker_block",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev2["timestamp"], prev["timestamp"], current["timestamp"]],
            trigger_conditions=("breaker_block_bullish",),
            parameters={"atr_period": config.atr_period},
            confirmed=True,
            invalidation_level=float(prev["close"]),
        )
    if float(current["close"]) < float(prev["close"]) < float(prev2["close"]):
        return ICTEvent(
            event_type="breaker_block",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[prev2["timestamp"], prev["timestamp"], current["timestamp"]],
            trigger_conditions=("breaker_block_bearish",),
            parameters={"atr_period": config.atr_period},
            confirmed=True,
            invalidation_level=float(prev["close"]),
        )
    return None


__all__ = [
    "detect_bullish_order_block",
    "detect_bearish_order_block",
    "detect_mitigation",
    "detect_breaker_block",
]
