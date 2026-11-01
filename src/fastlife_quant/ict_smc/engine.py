from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from fastlife_quant.ict_smc.atr import compute_atr
from fastlife_quant.ict_smc.config import DEFAULT_ICT_SMC_CONFIG, ICTSMCConfig
from fastlife_quant.ict_smc.context import (
    detect_discount,
    detect_equilibrium,
    detect_ote,
    detect_premium,
    multi_timeframe_analysis,
)
from fastlife_quant.ict_smc.events import ICTEvent
from fastlife_quant.ict_smc.imbalance import (
    detect_bearish_fvg,
    detect_bullish_fvg,
    detect_displacement,
    detect_inverse_fvg,
)
from fastlife_quant.ict_smc.liquidity import (
    detect_bsl,
    detect_equal_highs,
    detect_equal_lows,
    detect_inducement,
    detect_liquidity_sweep,
    detect_ssl,
)
from fastlife_quant.ict_smc.market_structure import (
    detect_bos,
    detect_choch,
    detect_external_structure,
    detect_internal_structure,
    detect_mss,
    detect_swing_high,
    detect_swing_low,
)
from fastlife_quant.ict_smc.order_blocks import (
    detect_bearish_order_block,
    detect_bullish_order_block,
    detect_breaker_block,
    detect_mitigation,
)


class ICTSMCEngine:
    """Moteur ICT/SMC explicable et sans look-ahead.

    Les detecteurs ne doivent jamais utiliser de donnees futures; chaque evenement
    est calcule a partir d'un prefixe de donnees connu jusqu'a l'indice courant.
    """

    def __init__(self, config: ICTSMCConfig | None = None) -> None:
        self.config = config or DEFAULT_ICT_SMC_CONFIG

    def analyze(self, df: pd.DataFrame, timeframe: str = "M5") -> list[dict[str, Any]]:
        if df.empty:
            return []
        events: list[dict[str, Any]] = []
        window = df.copy()
        if "timeframe" not in window.columns:
            window["timeframe"] = timeframe
        for idx in range(len(window)):
            snapshot = window.iloc[: idx + 1].copy()
            events.extend(self._scan_snapshot(snapshot, idx))
        return events

    def _scan_snapshot(self, df: pd.DataFrame, idx: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        for detector in (
            detect_swing_high,
            detect_swing_low,
            detect_bos,
            detect_choch,
            detect_mss,
            detect_bsl,
            detect_ssl,
            detect_equal_highs,
            detect_equal_lows,
            detect_liquidity_sweep,
            detect_inducement,
            detect_bullish_fvg,
            detect_bearish_fvg,
            detect_inverse_fvg,
            detect_displacement,
            detect_bullish_order_block,
            detect_bearish_order_block,
            detect_breaker_block,
            detect_mitigation,
            detect_premium,
            detect_discount,
            detect_equilibrium,
            detect_ote,
            detect_internal_structure,
            detect_external_structure,
        ):
            try:
                result = detector(df, idx, self.config)
            except Exception:
                result = None
            if isinstance(result, ICTEvent):
                events.append(result.as_dict())
        return events


__all__ = ["ICTSMCEngine"]
