from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
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


class RiskManager:
    """Gestion de risque structurale et de position sizing.

    Les regles de risk management ne doivent jamais etre depassees par le moteur.
    Aucun ordre reel n'est execute ici; cette couche ne produit que des calculs
    et des validations de setup.
    """

    def __init__(self, params: RiskParameters) -> None:
        self.params = params

    def evaluate_trade(self, entry: float, stop_loss: float, take_profit: float, *, daily_trades: int = 0) -> PositionSizing:
        if stop_loss <= 0 or entry <= 0:
            return PositionSizing(0.0, 0.0, 0.0, 0.0, self.params.max_daily_trades, False, "entry_or_stop_invalid")
        stop_distance = abs(entry - stop_loss)
        if stop_distance <= 0:
            return PositionSizing(0.0, 0.0, 0.0, 0.0, self.params.max_daily_trades, False, "stop_distance_zero")

        risk_amount = self.params.account_balance * self.params.risk_per_trade
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0.0
        rr = abs(take_profit - entry) / stop_distance if stop_distance > 0 else 0.0
        valid = rr >= self.params.min_rr and daily_trades < self.params.max_daily_trades
        reason = None if valid else "rr_or_daily_cap_violation"
        return PositionSizing(
            risk_amount=risk_amount,
            stop_distance=stop_distance,
            position_size=position_size,
            take_profit=take_profit,
            max_trades_per_day=self.params.max_daily_trades,
            valid=valid,
            reason=reason,
            metadata={"rr": rr, "risk_pct": self.params.risk_per_trade},
        )

    def check_daily_limit(self, daily_loss: float) -> bool:
        return daily_loss <= self.params.account_balance * self.params.max_daily_loss_pct


__all__ = ["RiskManager", "RiskParameters", "PositionSizing"]
