"""Construction de timeframes superieurs a partir d'un timeframe inferieur.

Principes :
- Aucune bougie n'est fabriquee : un bucket sans donnees n'existe pas.
- Chaque bougie agregee porte `n_bars` (bougies sources) et `coverage`
  (n_bars / attendu). Les buckets sous `min_coverage` sont ECARTES et comptes.
- Alignement : par defaut les buckets sont ancres sur minuit UTC. Les bougies
  H4/D1 d'un broker sont ancrees sur l'heure serveur : pour un alignement
  identique au broker, privilegier l'import natif de H4/D1 depuis MT5, ou fixer
  `anchor` (ex. pd.Timedelta(hours=22) si le jour broker demarre a 22:00 UTC).
- Le marche de l'or a une pause quotidienne : une bougie D1 complete a donc une
  couverture < 1 en M5. Regler `min_coverage` en consequence (explicite).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fastlife_quant.data import Timeframe


@dataclass
class ResampleResult:
    data: pd.DataFrame
    n_buckets_dropped_low_coverage: int


def resample_ohlcv(
    df: pd.DataFrame,
    src: Timeframe,
    dst: Timeframe,
    min_coverage: float = 1.0,
    anchor: pd.Timedelta = pd.Timedelta(0),
) -> ResampleResult:
    if dst.seconds <= src.seconds or dst.seconds % src.seconds != 0:
        raise ValueError(f"{dst.value} n'est pas un multiple strict de {src.value}")
    if not 0 < min_coverage <= 1:
        raise ValueError("min_coverage doit etre dans ]0, 1]")
    if df.empty:
        return ResampleResult(df.iloc[0:0].copy(), 0)
    if not df["timestamp"].is_monotonic_increasing or df["timestamp"].duplicated().any():
        raise ValueError("serie source non triee ou avec doublons : nettoyer d'abord (clean_ohlcv)")

    expected = dst.seconds // src.seconds
    indexed = df.set_index("timestamp")
    origin = pd.Timestamp("1970-01-01", tz="UTC") + anchor
    rule = pd.Timedelta(seconds=dst.seconds)
    g = indexed.resample(rule, origin=origin, closed="left", label="left")

    out = pd.DataFrame(
        {
            "open": g["open"].first(),
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].last(),
            "n_bars": g["open"].count(),
        }
    )
    if "volume" in indexed.columns:
        out["volume"] = g["volume"].sum(min_count=1)
    if "spread" in indexed.columns:
        out["spread"] = g["spread"].mean()

    out = out[out["n_bars"] > 0]  # buckets vides : inexistants, jamais crees
    out["coverage"] = out["n_bars"] / expected
    keep = out["coverage"] >= min_coverage
    dropped = int((~keep).sum())
    out = out[keep].reset_index()
    out["n_bars"] = out["n_bars"].astype(int)
    return ResampleResult(out, dropped)
