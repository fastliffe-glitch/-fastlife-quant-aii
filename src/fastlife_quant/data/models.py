"""Modeles de donnees de marche.

Chaque donnee porte sa source, son horodatage (UTC), son timeframe et son
statut de validation. La distinction REAL / SIMULATED / UNAVAILABLE est
explicite pour ne jamais presenter du simule comme du reel.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Timeframe(str, Enum):
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"

    @property
    def seconds(self) -> int:
        return _TF_SECONDS[self]

    @property
    def delta(self) -> timedelta:
        return timedelta(seconds=self.seconds)


_TF_SECONDS = {
    Timeframe.M5: 300,
    Timeframe.M15: 900,
    Timeframe.H1: 3600,
    Timeframe.H4: 14400,
    Timeframe.D1: 86400,
}


class DataSource(str, Enum):
    MT5 = "mt5"
    CSV = "csv"
    EXTERNAL = "external"
    TEST_FIXTURE = "test_fixture"


class DataKind(str, Enum):
    """Nature de la donnee : jamais melanger reel et simule."""

    REAL = "real"
    SIMULATED = "simulated"
    UNAVAILABLE = "unavailable"


class ValidationStatus(str, Enum):
    UNVALIDATED = "unvalidated"
    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    INVALID = "invalid"


class Candle(BaseModel):
    """Une bougie OHLCV avec sa provenance."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    timeframe: Timeframe
    source: DataSource
    kind: DataKind
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    spread: float | None = None
    status: ValidationStatus = ValidationStatus.UNVALIDATED

    @field_validator("timestamp")
    @classmethod
    def _utc_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("timestamp doit etre tz-aware (UTC)")
        return v.astimezone(timezone.utc)

    @field_validator("volume", "spread")
    @classmethod
    def _non_negative(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("volume et spread ne peuvent pas etre negatifs")
        return v

    @model_validator(mode="after")
    def _ohlc_consistent(self) -> "Candle":
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("les prix doivent etre strictement positifs")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high doit etre >= open, close et low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low doit etre <= open, close et high")
        return self


class SeriesMetadata(BaseModel):
    """Provenance d'une serie de bougies."""

    symbol: str = "XAUUSD"
    timeframe: Timeframe
    source: DataSource
    kind: DataKind
    status: ValidationStatus = ValidationStatus.UNVALIDATED
