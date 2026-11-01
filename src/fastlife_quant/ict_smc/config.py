from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ICTSMCConfig:
    """Parametres de reference de la Phase 3.

    Les valeurs par defaut suivent les meilleures pratiques ICT/SMC pour XAUUSD
    et sont toutes editables sans changer le code.
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

__all__ = ["ICTSMCConfig", "DEFAULT_ICT_SMC_CONFIG"]
