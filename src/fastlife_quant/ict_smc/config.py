from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ICTEvent:
    """Evenement explicable genere par un detecteur ICT/SMC."""

    event_type: str
    direction: str
    timeframe: str
    timestamp: pd.Timestamp
    price: float
    reference_bars: list[pd.Timestamp]
    trigger_conditions: tuple[str, ...]
    parameters: dict[str, Any]
    confirmed: bool
    invalidation_level: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "direction": self.direction,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "price": self.price,
            "reference_bars": self.reference_bars,
            "trigger_conditions": list(self.trigger_conditions),
            "parameters": self.parameters,
            "confirmed": self.confirmed,
            "invalidation_level": self.invalidation_level,
            "metadata": self.metadata,
        }


__all__ = ["ICTEvent"]
