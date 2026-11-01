from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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


class RiskEngine:
    """Moteur de gestion du risque et du position sizing.

    Les plans produits sont calcules de facon transparente et ne doivent pas conduire
    a un ordre reel. Le moteur applique les regles de protection du capital : RR min,
    max 3 trades/jour, protection contre la perte excessive.
    """

    def __init__(self, parameters: RiskParameters) -> None:
        self.parameters = parameters

    def size_position(self, entry: float, stop_loss: float, take_profit: float, *, daily_trades: int = 0) -> PositionSizing:
        if entry <= 0 or stop_loss <= 0:
            return PositionSizing(0.0, 0.0, 0.0, 0.0, self.parameters.max_daily_trades, False, "entry_or_stop_invalid")

        stop_distance = abs(entry - stop_loss)
        if stop_distance <= 0:
            return PositionSizing(0.0, 0.0, 0.0, 0.0, self.parameters.max_daily_trades, False, "stop_distance_zero")

        risk_amount = self.parameters.account_balance * self.parameters.risk_per_trade
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0.0
        rr = abs(take_profit - entry) / stop_distance if stop_distance > 0 else 0.0
        valid = rr >= self.parameters.min_rr and daily_trades < self.parameters.max_daily_trades
        return PositionSizing(
            risk_amount=risk_amount,
            stop_distance=stop_distance,
            position_size=position_size,
            take_profit=take_profit,
            max_trades_per_day=self.parameters.max_daily_trades,
            valid=valid,
            reason=None if valid else "rr_or_daily_cap_violation",
            metadata={"rr": rr, "risk_pct": self.parameters.risk_per_trade},
        )

    def generate_trade_plan(
        self,
        *,
        setup_name: str,
        symbol: str,
        entry: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        session: str,
        timeframe: str,
        daily_trades: int = 0,
    ) -> TradePlan | None:
        sizing = self.size_position(entry, stop_loss, take_profit, daily_trades=daily_trades)
        if not sizing.valid:
            return None
        return TradePlan(
            setup_name=setup_name,
            symbol=symbol,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=sizing.position_size,
            risk_per_trade=self.parameters.risk_per_trade,
            confidence=confidence,
            session=session,
            timeframe=timeframe,
            metadata={"risk_amount": sizing.risk_amount, "rr": sizing.metadata.get("rr", 0.0)},
        )

    def daily_loss_guard(self, daily_loss_value: float) -> bool:
        return daily_loss_value <= self.parameters.account_balance * self.parameters.max_daily_loss_pct


__all__ = ["PositionSizing", "RiskEngine", "RiskParameters", "TradePlan"]
