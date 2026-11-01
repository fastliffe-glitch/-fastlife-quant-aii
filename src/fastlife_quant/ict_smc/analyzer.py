"""Analyse ICT/SMC complete d'une serie OHLCV validee."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from fastlife_quant.data import Timeframe, validate_ohlcv
from fastlife_quant.ict_smc.config import ICTConfig
from fastlife_quant.ict_smc.events import Event
from fastlife_quant.ict_smc.fvg import detect_fvgs
from fastlife_quant.ict_smc.indicators import atr as compute_atr
from fastlife_quant.ict_smc.liquidity import LiquidityResult, detect_liquidity
from fastlife_quant.ict_smc.order_blocks import detect_order_blocks
from fastlife_quant.ict_smc.structure import detect_structure
from fastlife_quant.ict_smc.swings import Swing, detect_swings
from fastlife_quant.ict_smc.tracking import ZoneTracking, derive_inverse_zones, track_zones


@dataclass
class Analysis:
    config: ICTConfig
    atr: np.ndarray
    swings: list[Swing]
    external_swings: list[Swing]
    structure: list[Event]  # BOS / CHOCH / MSS (interne)
    external_structure: list[Event]
    internal_trend: np.ndarray
    fvgs: list[Event]
    order_blocks: list[Event]
    liquidity: LiquidityResult
    trackings: list[ZoneTracking]
    inverse_zones: list[Event]  # IFVG et BREAKER

    def all_events(self) -> list[Event]:
        evs = [
            *self.structure, *self.external_structure, *self.fvgs, *self.order_blocks,
            *self.liquidity.events, *self.inverse_zones,
        ]
        return sorted(evs, key=lambda e: (e.detected_idx, e.kind, e.direction or ""))


def analyze(df: pd.DataFrame, timeframe: Timeframe, cfg: ICTConfig = ICTConfig()) -> Analysis:
    """Refuse une serie invalide. Les trous (warnings) sont toleres."""
    report = validate_ohlcv(df, timeframe)
    if report.errors:
        raise ValueError("serie invalide : " + "; ".join(f"{e.code} ({e.count})" for e in report.errors))
    df = df.reset_index(drop=True)

    a = compute_atr(df, cfg.atr.period)
    swings = detect_swings(df, cfg.swing)
    ext_swings = detect_swings(df, cfg.external_swing)
    internal = detect_structure(df, swings, a, cfg.structure, "internal")
    external = detect_structure(df, ext_swings, a, cfg.structure, "external")
    fvgs = detect_fvgs(df, a, cfg.fvg)
    obs = detect_order_blocks(df, a, internal.events, cfg.order_block)
    liq = detect_liquidity(df, swings, a, cfg.liquidity)
    trackings = track_zones(df, fvgs + obs)
    inverse = derive_inverse_zones(df, trackings)
    return Analysis(cfg, a, swings, ext_swings, internal.events, external.events, internal.trend, fvgs, obs, liq, trackings, inverse)
