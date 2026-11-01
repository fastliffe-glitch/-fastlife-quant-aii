from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    """Surface de visualisation investisseur pour iPhone / navigateur.

    Cette interface sert uniquement a representer l'etat des analyses et des
    resultats de tests, sans exécution directe d'ordres ni donnees reelles non
    verifiees.
    """

    def __init__(self) -> None:
        self.state = DashboardState()

    def refresh(self, snapshot: dict[str, Any]) -> DashboardState:
        self.state = DashboardState(
            overview=[DashboardPanel("market", "ready", snapshot.get("market"), {})],
            market_context=snapshot.get("market_context", {}),
            risk_context=snapshot.get("risk_context", {}),
            historical=snapshot.get("historical", []),
            metadata={"source": "analysis_only"},
        )
        return self.state


__all__ = ["DashboardPanel", "DashboardState", "MarketDashboard"]
