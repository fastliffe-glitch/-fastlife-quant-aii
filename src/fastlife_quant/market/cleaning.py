"""Nettoyage conservateur d'une serie OHLCV.

Regles (aucune donnee n'est jamais inventee, comblee ou interpolee) :
- doublons EXACTS (meme timestamp, memes valeurs) : on garde le premier.
- doublons CONFLICTUELS (meme timestamp, valeurs differentes) : aucun choix
  arbitraire, toutes les lignes sont mises en quarantaine.
- lignes invalides (NaN, prix <= 0, OHLC incoherent, volume/spread negatif) :
  mises en quarantaine, avec la raison.
- serie desordonnee : simple tri par timestamp (rien n'est modifie ailleurs).
Tout ce qui est retire est conserve dans `quarantine` : rien ne disparait.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fastlife_quant.data import Timeframe, ValidationReport, validate_ohlcv

_PRICES = ["open", "high", "low", "close"]


@dataclass
class CleaningResult:
    clean: pd.DataFrame
    quarantine: pd.DataFrame  # colonnes d'origine + `reason`
    n_input: int
    n_exact_duplicates_dropped: int
    n_conflicting_rows: int
    was_resorted: bool
    report: ValidationReport  # validation de `clean`


def clean_ohlcv(df: pd.DataFrame, timeframe: Timeframe) -> CleaningResult:
    n_input = len(df)
    work = df.copy()
    reasons = pd.Series("", index=work.index, dtype=object)

    def flag(mask: pd.Series, reason: str) -> None:
        reasons[mask & (reasons == "")] = reason

    was_resorted = not work["timestamp"].is_monotonic_increasing

    # Doublons conflictuels : meme timestamp avec valeurs differentes.
    value_cols = [c for c in work.columns if c != "timestamp"]
    dup_ts = work["timestamp"].duplicated(keep=False)
    full_dup = work.duplicated(subset=["timestamp", *value_cols], keep=False)
    conflicting = dup_ts & ~full_dup
    flag(conflicting, "conflicting_duplicate")

    # Lignes invalides.
    prices = work[_PRICES]
    flag(prices.isna().any(axis=1), "price_nan")
    flag((prices <= 0).any(axis=1), "price_non_positive")
    flag(
        (work["high"] < work[["open", "close", "low"]].max(axis=1))
        | (work["low"] > work[["open", "close", "high"]].min(axis=1)),
        "ohlc_inconsistent",
    )
    for col in ("volume", "spread"):
        if col in work.columns:
            flag(work[col] < 0, f"{col}_negative")

    quarantine = work[reasons != ""].assign(reason=reasons[reasons != ""])
    kept = work[reasons == ""]

    before = len(kept)
    kept = kept.drop_duplicates(subset=["timestamp", *value_cols], keep="first")
    n_exact = before - len(kept)

    kept = kept.sort_values("timestamp", kind="stable").reset_index(drop=True)
    return CleaningResult(
        clean=kept,
        quarantine=quarantine.reset_index(drop=True),
        n_input=n_input,
        n_exact_duplicates_dropped=n_exact,
        n_conflicting_rows=int(conflicting.sum()),
        was_resorted=was_resorted,
        report=validate_ohlcv(kept, timeframe),
    )
