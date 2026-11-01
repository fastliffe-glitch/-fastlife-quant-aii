from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class DashboardPanel:
    name: str
    status: str
    value: Any = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardState:
    overview: list[DashboardPanel] = field(default_factory=list)
    market_context: dict[str, Any] = field(default_factory=dict)
    risk_context: dict[str, Any] = field(default_factory=dict)
    historical: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MarketDashboard:
    """Le dashboard mobile doit representer les resultats de l'analyse, pas des
    predictions non supportees par des donnees.
    """

    def __init__(self) -> None:
        self.state = DashboardState()

    def refresh(self, snapshot: dict[str, Any]) -> DashboardState:
        overview = [
            DashboardPanel("market", "ready", snapshot.get("market"), {}),
            DashboardPanel("risk", snapshot.get("risk_status", "unknown"), snapshot.get("risk_value"), {}),
            DashboardPanel("macro", snapshot.get("macro_status", "unknown"), snapshot.get("macro_value"), {}),
        ]
        self.state = DashboardState(
            overview=overview,
            market_context=snapshot.get("market_context", {}),
            risk_context=snapshot.get("risk_context", {}),
            historical=snapshot.get("historical", []),
            metadata={"source": "analysis_only"},
        )
        return self.state


__all__ = ["DashboardPanel", "DashboardState", "MarketDashboard"]
