"""Evenement de detection explicable.

Chaque detection garde : les bougies exactes (index, heure, valeurs) qui l'ont
declenchee, les conditions evaluees (texte avec les chiffres) et des metriques.
`detected_idx` est la bougie a la CLOTURE de laquelle l'evenement devient connu :
aucune decision ne doit l'utiliser avant cette bougie (pas de look-ahead).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class Evidence:
    label: str
    idx: int
    time: pd.Timestamp
    values: dict[str, float]


@dataclass(frozen=True)
class Event:
    kind: str
    direction: str | None  # "bullish" / "bearish" : geometrie du motif, pas une prediction
    detected_idx: int
    detected_time: pd.Timestamp
    evidence: tuple[Evidence, ...]
    conditions: tuple[str, ...]
    metrics: dict[str, float] = field(default_factory=dict)

    def key(self) -> tuple:
        """Identite comparable (utilisee par les tests d'invariance de prefixe)."""
        return (self.kind, self.direction, self.detected_idx, tuple(sorted(self.metrics.items())))

    def explain(self) -> str:
        head = f"{self.kind}" + (f" {self.direction}" if self.direction else "")
        lines = [f"{head} - connu a la cloture de la bougie #{self.detected_idx} ({self.detected_time})"]
        lines.append("  Bougies :")
        for e in self.evidence:
            vals = ", ".join(f"{k}={v:g}" for k, v in e.values.items())
            lines.append(f"    - {e.label}: #{e.idx} {e.time} ({vals})")
        lines.append("  Conditions :")
        lines.extend(f"    - {c}" for c in self.conditions)
        if self.metrics:
            lines.append("  Metriques : " + ", ".join(f"{k}={v:g}" for k, v in self.metrics.items()))
        return "\n".join(lines)


def bar_evidence(df: pd.DataFrame, i: int, label: str, fields: tuple[str, ...] = ("open", "high", "low", "close")) -> Evidence:
    return Evidence(label, i, df["timestamp"].iloc[i], {f: float(df[f].iloc[i]) for f in fields})
