from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PerformanceMetrics:
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    expectancy: float
    profit_factor: float
    average_win: float
    average_loss: float
    max_drawdown: float
    mean_r: float
    std_r: float


@dataclass
class TradeRecord:
    pnl: float
    setup: str
    timeframe: str
    session: str
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class QuantEngine:
    """Moteur quantitatif correspondant au programme d'analyse de performance.

    Cette couche agit sur des trades ou des resultats de backtest, sans produire de
    fausses donnees. Elle calcule des metriques explicables et les compare par setup,
    timeframe et session.
    """

    def summarize(self, trades: list[TradeRecord]) -> PerformanceMetrics:
        if not trades:
            return PerformanceMetrics(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        pnl_values = [trade.pnl for trade in trades]
        wins = [trade.pnl for trade in trades if trade.pnl > 0]
        losses = [trade.pnl for trade in trades if trade.pnl < 0]
        gross_wins = sum(wins)
        gross_losses = abs(sum(losses))
        mean_r = sum(pnl_values) / len(pnl_values)
        variance = sum((value - mean_r) ** 2 for value in pnl_values) / len(pnl_values)
        std_r = variance ** 0.5
        peak = 0.0
        running = 0.0
        max_drawdown = 0.0
        for value in pnl_values:
            running += value
            if running > peak:
                peak = running
            max_drawdown = max(max_drawdown, peak - running)

        return PerformanceMetrics(
            total_trades=len(trades),
            wins=len(wins),
            losses=len(losses),
            win_rate=(len(wins) / len(trades)) if trades else 0.0,
            expectancy=(sum(pnl_values) / len(pnl_values)) if pnl_values else 0.0,
            profit_factor=(gross_wins / gross_losses) if gross_losses else (float("inf") if gross_wins else 0.0),
            average_win=(sum(wins) / len(wins)) if wins else 0.0,
            average_loss=(abs(sum(losses)) / len(losses)) if losses else 0.0,
            max_drawdown=max_drawdown,
            mean_r=mean_r,
            std_r=std_r,
        )

    def group_by_setup(self, trades: list[TradeRecord]) -> dict[str, PerformanceMetrics]:
        grouped: dict[str, list[TradeRecord]] = {}
        for trade in trades:
            grouped.setdefault(trade.setup, []).append(trade)
        return {name: self.summarize(items) for name, items in grouped.items()}

    def group_by_timeframe(self, trades: list[TradeRecord]) -> dict[str, PerformanceMetrics]:
        grouped: dict[str, list[TradeRecord]] = {}
        for trade in trades:
            grouped.setdefault(trade.timeframe, []).append(trade)
        return {name: self.summarize(items) for name, items in grouped.items()}

    def compare_configurations(self, configurations: dict[str, list[TradeRecord]]) -> dict[str, PerformanceMetrics]:
        return {name: self.summarize(items) for name, items in configurations.items()}


__all__ = ["PerformanceMetrics", "QuantEngine", "TradeRecord"]
