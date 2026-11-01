"""Configuration du moteur ICT/SMC. Toutes les definitions sont parametrables.

Les valeurs par defaut sont des references raisonnables, PAS des valeurs
optimisees sur des resultats. Ne pas les ajuster pour "ameliorer" un backtest.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SwingConfig:
    left: int = 3
    right: int = 3  # delai de confirmation : un swing n'est connu qu'apres `right` bougies

    def __post_init__(self) -> None:
        if self.left < 1 or self.right < 1:
            raise ValueError("left et right doivent etre >= 1")


@dataclass(frozen=True)
class ATRConfig:
    period: int = 14

    def __post_init__(self) -> None:
        if self.period < 1:
            raise ValueError("period doit etre >= 1")


@dataclass(frozen=True)
class StructureConfig:
    break_on: str = "close"  # "close" (cassure par cloture) ou "wick" (par meche)
    mss_displacement_atr_mult: float = 1.0  # CHoCH + corps >= mult * ATR => MSS

    def __post_init__(self) -> None:
        if self.break_on not in ("close", "wick"):
            raise ValueError("break_on doit etre 'close' ou 'wick'")
        if self.mss_displacement_atr_mult < 0:
            raise ValueError("mss_displacement_atr_mult doit etre >= 0")


@dataclass(frozen=True)
class FVGConfig:
    min_atr_mult: float = 0.1  # taille min du gap en multiple d'ATR ; 0 = pas de filtre

    def __post_init__(self) -> None:
        if self.min_atr_mult < 0:
            raise ValueError("min_atr_mult doit etre >= 0")


@dataclass(frozen=True)
class OrderBlockConfig:
    displacement_atr_mult: float = 1.5  # deplacement net >= mult * ATR
    displacement_bars: int = 1  # nombre de bougies consecutives du deplacement
    max_lookback_bars: int = 10  # recherche de la bougie opposee avant le deplacement
    zone: str = "body"  # "body" (open-close) ou "range" (high-low)
    require_structure_break: bool = True
    accepted_breaks: tuple[str, ...] = ("BOS", "MSS")
    confirm_window_bars: int = 5  # la cassure doit survenir dans [d, d+window]

    def __post_init__(self) -> None:
        if self.zone not in ("body", "range"):
            raise ValueError("zone doit etre 'body' ou 'range'")
        if self.displacement_bars < 1 or self.max_lookback_bars < 1 or self.confirm_window_bars < 0:
            raise ValueError("parametres de fenetre invalides")
        if self.displacement_atr_mult < 0:
            raise ValueError("displacement_atr_mult doit etre >= 0")


@dataclass(frozen=True)
class LiquidityConfig:
    equal_tolerance_atr_mult: float = 0.1  # egalite si ecart <= mult * ATR
    equal_max_separation_bars: int = 200
    reclaim_bars: int = 1  # le prix doit re-cloturer sous/sur le niveau dans N bougies

    def __post_init__(self) -> None:
        if self.reclaim_bars < 1:
            raise ValueError("reclaim_bars doit etre >= 1")
        if self.equal_tolerance_atr_mult < 0:
            raise ValueError("equal_tolerance_atr_mult doit etre >= 0")


@dataclass(frozen=True)
class FibConfig:
    ote: tuple[float, float] = (0.62, 0.79)
    golden_zone: tuple[float, float] = (0.618, 0.65)


@dataclass(frozen=True)
class ICTConfig:
    swing: SwingConfig = field(default_factory=SwingConfig)  # structure interne
    external_swing: SwingConfig = field(default_factory=lambda: SwingConfig(10, 10))
    atr: ATRConfig = field(default_factory=ATRConfig)
    structure: StructureConfig = field(default_factory=StructureConfig)
    fvg: FVGConfig = field(default_factory=FVGConfig)
    order_block: OrderBlockConfig = field(default_factory=OrderBlockConfig)
    liquidity: LiquidityConfig = field(default_factory=LiquidityConfig)
    fib: FibConfig = field(default_factory=FibConfig)
