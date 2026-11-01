from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    symbol: str = "XAUUSD"
    start: str = "2024-01-01"
    end: str = "2024-12-31"
    timeframe: str = "H1"
    spread: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    initial_balance: float = 10000.0
    risk_per_trade: float = 0.01
    max_daily_trades: int = 3
    no_lookahead: bool = True


@dataclass
class BacktestTrade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    pnl: float
    setup: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResult:
    config: BacktestConfig
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    total_pnl: float = 0.0
    win_rate: float = 0.0
    expectancy: float = 0.0
    max_drawdown: float = 0.0


class BacktestEngine:
    """Backtest historique, sans look-ahead bias, sans exécution réelle."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(self, dataframe: pd.DataFrame, signals: list[dict[str, Any]]) -> BacktestResult:
        if dataframe.empty:
            return BacktestResult(self.config)
        equity = [float(self.config.initial_balance)]
        trades: list[BacktestTrade] = []
        for signal in signals:
            ts = pd.Timestamp(signal.get("timestamp"))
            if ts not in dataframe["timestamp"].values:
                continue
            pnl = float(signal.get("pnl", 0.0))
            trades.append(
                BacktestTrade(
                    entry_time=ts,
                    exit_time=ts,
                    pnl=pnl,
                    setup=str(signal.get("event_type", "unknown")),
                    confidence=float(signal.get("confidence", 0.0)),
                    metadata={"event": signal},
                )
            )
            equity.append(equity[-1] + pnl)
        total_pnl = sum(t.pnl for t in trades)
        wins = sum(1 for t in trades if t.pnl > 0)
        total = len(trades)
        return BacktestResult(
            config=self.config,
            trades=trades,
            equity_curve=equity,
            total_pnl=total_pnl,
            win_rate=wins / total if total else 0.0,
            expectancy=total_pnl / total if total else 0.0,
            max_drawdown=0.0,
        )


__all__ = ["BacktestConfig", "BacktestEngine", "BacktestResult", "BacktestTrade"]
