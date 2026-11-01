from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from fastlife_quant.ict_smc.engine import ICTSMCEngine
from fastlife_quant.quant.engine import QuantEngine, TradeRecord
from fastlife_quant.risk.engine import RiskEngine, RiskParameters


@dataclass
class LabContext:
    symbol: str = "XAUUSD"
    timeframe: str = "M5"
    risk_parameters: RiskParameters | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class FASTLIFEQuantLab:
    """Orchestrateur principal de FASTLIFE QUANT AI.

    Cette couche relie le moteur ICT/SMC, le moteur quant et le moteur de risque.
    Elle ne remplace pas les donnees externes mais structure les calculs et la logique
    d'analyse en sequence explicable.
    """

    def __init__(self, context: LabContext | None = None) -> None:
        self.context = context or LabContext()
        self.ict = ICTSMCEngine()
        self.quant = QuantEngine()
        self.risk = RiskEngine(self.context.risk_parameters or RiskParameters(account_balance=10000.0))

    def analyze(self, dataframe: pd.DataFrame, *, timeframe: str | None = None) -> dict[str, Any]:
        tf = timeframe or self.context.timeframe
        events = self.ict.analyze(dataframe.copy(), timeframe=tf)
        trades = [
            TradeRecord(
                pnl=float(event.get("price", 0.0)),
                setup=str(event.get("event_type", "unknown")),
                timeframe=tf,
                session="OFF",
                confidence=1.0 if event.get("confirmed") else 0.5,
                metadata={"raw": event},
            )
            for event in events
        ]
        metrics = self.quant.summarize(trades)
        trade_plan = []
        for event in events[:3]:
            plan = self.risk.generate_trade_plan(
                setup_name=str(event.get("event_type", "unknown")),
                symbol=self.context.symbol,
                entry=float(event.get("price", 0.0)),
                stop_loss=float(event.get("price", 0.0)) - 10.0,
                take_profit=float(event.get("price", 0.0)) + 20.0,
                confidence=1.0 if event.get("confirmed") else 0.5,
                session="OFF",
                timeframe=tf,
                daily_trades=0,
            )
            if plan is not None:
                trade_plan.append(plan)

        return {
            "timeframe": tf,
            "event_count": len(events),
            "signals": events,
            "metrics": {
                "total_trades": metrics.total_trades,
                "wins": metrics.wins,
                "losses": metrics.losses,
                "win_rate": metrics.win_rate,
                "expectancy": metrics.expectancy,
                "profit_factor": metrics.profit_factor,
                "average_win": metrics.average_win,
                "average_loss": metrics.average_loss,
                "max_drawdown": metrics.max_drawdown,
            },
            "risk_plan": [
                {
                    "setup": plan.setup_name,
                    "symbol": plan.symbol,
                    "entry": plan.entry,
                    "stop_loss": plan.stop_loss,
                    "take_profit": plan.take_profit,
                    "position_size": plan.position_size,
                    "confidence": plan.confidence,
                }
                for plan in trade_plan
            ],
        }


__all__ = ["FASTLIFEQuantLab", "LabContext"]
