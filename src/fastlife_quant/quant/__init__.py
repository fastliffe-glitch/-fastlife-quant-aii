from __future__ import annotations

import pandas as pd

from fastlife_quant.ict_smc.config import ICTSMCConfig
from fastlife_quant.ict_smc.events import ICTEvent


def detect_premium(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 1:
        return None
    current = df.iloc[idx]
    high = df["high"].iloc[: idx + 1].max()
    low = df["low"].iloc[: idx + 1].min()
    range_size = high - low
    if range_size == 0:
        return None
    if (current["close"] - low) / range_size > config.premium_threshold:
        return ICTEvent(
            event_type="premium",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[df["timestamp"].iloc[: idx + 1].min(), df["timestamp"].iloc[: idx + 1].max()],
            trigger_conditions=("price_above_premium_zone",),
            parameters={"premium_threshold": config.premium_threshold},
            confirmed=True,
            invalidation_level=float(high),
        )
    return None


def detect_discount(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 1:
        return None
    current = df.iloc[idx]
    high = df["high"].iloc[: idx + 1].max()
    low = df["low"].iloc[: idx + 1].min()
    range_size = high - low
    if range_size == 0:
        return None
    if (high - current["close"]) / range_size > (1 - config.discount_threshold):
        return ICTEvent(
            event_type="discount",
            direction="bearish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(current["close"]),
            reference_bars=[df["timestamp"].iloc[: idx + 1].min(), df["timestamp"].iloc[: idx + 1].max()],
            trigger_conditions=("price_below_discount_zone",),
            parameters={"discount_threshold": config.discount_threshold},
            confirmed=True,
            invalidation_level=float(low),
        )
    return None


def detect_equilibrium(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    if idx < 1:
        return None
    current = df.iloc[idx]
    high = df["high"].iloc[: idx + 1].max()
    low = df["low"].iloc[: idx + 1].min()
    mid = (high + low) / 2
    if abs(float(current["close"]) - mid) <= abs(high - low) * 0.05:
        return ICTEvent(
            event_type="equilibrium",
            direction="neutral",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(mid),
            reference_bars=[df["timestamp"].iloc[: idx + 1].min(), df["timestamp"].iloc[: idx + 1].max()],
            trigger_conditions=("close_near_midpoint",),
            parameters={},
            confirmed=True,
            invalidation_level=float(mid),
        )
    return None


def detect_ote(df: pd.DataFrame, idx: int, config: ICTSMCConfig | None = None) -> ICTEvent | None:
    config = config or ICTSMCConfig()
    if idx < 1:
        return None
    current = df.iloc[idx]
    high = df["high"].iloc[: idx + 1].max()
    low = df["low"].iloc[: idx + 1].min()
    ote = low + (high - low) * config.ote_level
    if float(current["close"]) <= ote <= float(current["high"]) or float(current["low"]) <= ote <= float(current["close"]):
        return ICTEvent(
            event_type="ote",
            direction="bullish",
            timeframe=str(df["timeframe"].iloc[idx]) if "timeframe" in df.columns else "unknown",
            timestamp=current["timestamp"],
            price=float(ote),
            reference_bars=[df["timestamp"].iloc[: idx + 1].min(), df["timestamp"].iloc[: idx + 1].max()],
            trigger_conditions=("price_in_ote_range",),
            parameters={"ote_level": config.ote_level},
            confirmed=True,
            invalidation_level=float(ote),
        )
    return None


def multi_timeframe_analysis(df_map: dict[str, pd.DataFrame]) -> dict[str, object]:
    """Analyse multi-timeframe simple: renvoie les niveaux de tendance agreges."""
    summary: dict[str, object] = {}
    for tf, frame in df_map.items():
        if frame.empty:
            continue
        summary[tf] = {
            "last_close": float(frame["close"].iloc[-1]),
            "last_high": float(frame["high"].iloc[-1]),
            "last_low": float(frame["low"].iloc[-1]),
            "trend": "bullish" if frame["close"].iloc[-1] >= frame["close"].iloc[0] else "bearish",
        }
    return summary


__all__ = [
    "detect_premium",
    "detect_discount",
    "detect_equilibrium",
    "detect_ote",
    "multi_timeframe_analysis",
]
