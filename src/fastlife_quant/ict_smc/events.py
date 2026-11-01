from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class EventRef:
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


@dataclass
class ICTSMCConfig:
    """Parametres de reference pour le moteur ICT/SMC.

    Tous les seuils sont configurables sans modifier le code. Le moteur n'utilise
    jamais de donnees futures lors de la detection des evenements.
    """

    swing_left_bars: int = 3
    swing_right_bars: int = 3
    confirmation_only_closed: bool = True
    atr_period: int = 14
    atr_multiplier: float = 1.0
    fvg_atr_filter: float = 0.0
    order_block_atr_threshold: float = 1.0
    structural_confirmation_bars: int = 2
    min_displacement_atr: float = 1.0
    premium_threshold: float = 0.6
    discount_threshold: float = 0.4
    ote_level: float = 0.618


DEFAULT_ICT_SMC_CONFIG = ICTSMCConfig()
