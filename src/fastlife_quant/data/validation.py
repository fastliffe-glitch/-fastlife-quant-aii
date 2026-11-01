"""Validation des series OHLCV.

Principe : on DETECTE et on RAPPORTE les problemes, on ne corrige jamais et on
n'invente jamais de donnees manquantes (pas de forward-fill, pas
d'interpolation). Le DataFrame d'entree n'est jamais modifie.

Format attendu : colonnes `timestamp` (datetime tz-aware UTC), `open`, `high`,
`low`, `close`, et optionnellement `volume` et `spread`.

Regle des gaps : un trou est "attendu" (weekend) si la bougie precedente est un
vendredi, la suivante un dimanche ou lundi, et l'ecart <= 72 h. Tout autre trou
(jour ferie, donnees manquantes) est signale en avertissement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from fastlife_quant.data.models import SeriesMetadata, Timeframe, ValidationStatus

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close")
PRICE_COLUMNS = ("open", "high", "low", "close")
_MAX_WEEKEND_GAP = pd.Timedelta(hours=72)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    message: str
    count: int = 1


@dataclass
class ValidationReport:
    n_rows: int
    issues: list[Issue] = field(default_factory=list)
    expected_gaps: int = 0

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]

    @property
    def status(self) -> ValidationStatus:
        if self.errors:
            return ValidationStatus.INVALID
        if self.warnings:
            return ValidationStatus.VALID_WITH_WARNINGS
        return ValidationStatus.VALID

    def has(self, code: str) -> bool:
        return any(i.code == code for i in self.issues)


@dataclass
class ValidatedSeries:
    data: pd.DataFrame
    metadata: SeriesMetadata
    report: ValidationReport


def _add(report: ValidationReport, sev: Severity, code: str, msg: str, count: int = 1) -> None:
    report.issues.append(Issue(sev, code, msg, count))


def validate_ohlcv(df: pd.DataFrame, timeframe: Timeframe) -> ValidationReport:
    """Valide une serie OHLCV. Ne modifie pas `df`."""
    report = ValidationReport(n_rows=len(df))

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        _add(report, Severity.ERROR, "missing_columns", f"colonnes manquantes: {missing}", len(missing))
        return report
    if df.empty:
        _add(report, Severity.ERROR, "empty", "serie vide")
        return report

    ts = df["timestamp"]
    if not isinstance(ts.dtype, pd.DatetimeTZDtype):
        _add(report, Severity.ERROR, "timestamp_not_tz_aware", "timestamp doit etre datetime tz-aware")
        return report
    if str(ts.dt.tz) != "UTC":
        _add(report, Severity.ERROR, "timestamp_not_utc", f"timestamp doit etre en UTC (recu {ts.dt.tz})")
        return report
    if ts.isna().any():
        _add(report, Severity.ERROR, "timestamp_nan", "timestamps manquants", int(ts.isna().sum()))
        return report

    prices = df[list(PRICE_COLUMNS)]
    n_nan = int(prices.isna().any(axis=1).sum())
    if n_nan:
        _add(report, Severity.ERROR, "price_nan", "valeurs de prix manquantes (NaN)", n_nan)
    n_nonpos = int((prices <= 0).any(axis=1).sum())
    if n_nonpos:
        _add(report, Severity.ERROR, "price_non_positive", "prix <= 0", n_nonpos)

    n_dup = int(ts.duplicated().sum())
    if n_dup:
        _add(report, Severity.ERROR, "duplicate_timestamps", "timestamps dupliques", n_dup)
    if not ts.is_monotonic_increasing:
        _add(report, Severity.ERROR, "not_sorted", "timestamps non tries par ordre croissant")

    bad_high = int((df["high"] < df[["open", "close", "low"]].max(axis=1)).sum())
    bad_low = int((df["low"] > df[["open", "close", "high"]].min(axis=1)).sum())
    if bad_high or bad_low:
        _add(report, Severity.ERROR, "ohlc_inconsistent", "bougies avec high/low incoherents", bad_high + bad_low)

    for col in ("volume", "spread"):
        if col in df.columns and (df[col] < 0).any():
            _add(report, Severity.ERROR, f"{col}_negative", f"{col} negatif", int((df[col] < 0).sum()))

    _check_gaps(df["timestamp"], timeframe, report)
    return report


def _check_gaps(ts: pd.Series, timeframe: Timeframe, report: ValidationReport) -> None:
    if len(ts) < 2 or not ts.is_monotonic_increasing:
        return
    step = pd.Timedelta(seconds=timeframe.seconds)
    diffs = ts.diff().iloc[1:]
    prev = ts.shift(1).iloc[1:]
    gaps = diffs > step
    if not gaps.any():
        return
    is_weekend = (
        (prev.dt.weekday == 4)
        & ts.iloc[1:].dt.weekday.isin([6, 0])
        & (diffs <= _MAX_WEEKEND_GAP)
    )
    unexpected = gaps & ~is_weekend
    report.expected_gaps = int((gaps & is_weekend).sum())
    if unexpected.any():
        missing_bars = int(((diffs[unexpected] / step) - 1).round().sum())
        _add(
            report,
            Severity.WARNING,
            "unexpected_gaps",
            f"{int(unexpected.sum())} trou(s) hors weekend (~{missing_bars} bougies absentes, non comblees)",
            int(unexpected.sum()),
        )


def validate_series(df: pd.DataFrame, metadata: SeriesMetadata) -> ValidatedSeries:
    """Valide une serie et renvoie ses metadonnees avec le statut mis a jour."""
    report = validate_ohlcv(df, metadata.timeframe)
    new_meta = metadata.model_copy(update={"status": report.status})
    return ValidatedSeries(data=df, metadata=new_meta, report=report)
