from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class RiskParameters:
    account_balance: float
    risk_per_trade: float = 0.01
    rr_ratio: float = 2.0
    max_daily_trades: int = 3
    max_daily_loss_pct: float = 0.03
    min_rr: float = 2.0
    spread_pips: float = 0.0
    slippage_pips: float = 0.0


@dataclass
class PositionSizing:
    risk_amount: float
    stop_distance: float
    position_size: float
    take_profit: float
    max_trades_per_day: int
    valid: bool
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TradePlan:
    setup_name: str
    symbol: str
    entry: float
    stop_loss: float
    take_profit: float
    position_size: float
    risk_per_trade: float
    confidence: float = 0.0
    session: str = "OFF"
    timeframe: str = "M5"
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["RiskParameters", "PositionSizing", "TradePlan"]
