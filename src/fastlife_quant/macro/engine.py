from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EconomicRelease:
    name: str
    date: str
    impact: str
    currency: str
    expected: float | None = None
    actual: float | None = None
    source: str = "manual"


@dataclass
class MacroSnapshot:
    timestamp: str
    dxy: float | None = None
    us10y: float | None = None
    us2y: float | None = None
    cpi: float | None = None
    pce: float | None = None
    ppi: float | None = None
    nfp: float | None = None
    wti: float | None = None
    brent: float | None = None
    monetary_policy: str = "unknown"
    geopolitical_risk: str = "baseline"
    releases: list[EconomicRelease] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MacroIntelligence:
    """Contexte macroeconomique pour XAUUSD.

    Cette couche ne produit pas de prediction certifiee; elle structure les signaux,
    l'impact macro attendu et les evenements economiques proches.
    """

    def __init__(self, snapshot: MacroSnapshot | None = None) -> None:
        self.snapshot = snapshot or MacroSnapshot(timestamp="1970-01-01")

    def assess_impact(self) -> dict[str, Any]:
        release_names = [release.name for release in self.snapshot.releases]
        return {
            "symbol": "XAUUSD",
            "dxy": self.snapshot.dxy,
            "us10y": self.snapshot.us10y,
            "us2y": self.snapshot.us2y,
            "monetary_policy": self.snapshot.monetary_policy,
            "geopolitical_risk": self.snapshot.geopolitical_risk,
            "releases": release_names,
            "impact_note": "Contexte explicable; aucune prediction garantie.",
            "macro_bias": "mixed" if not release_names else "watchlist",
        }

    def add_release(self, release: EconomicRelease) -> None:
        self.snapshot.releases.append(release)


__all__ = ["EconomicRelease", "MacroIntelligence", "MacroSnapshot"]
