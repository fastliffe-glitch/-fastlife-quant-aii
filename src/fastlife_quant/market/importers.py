"""Lecture de fichiers d'historique (export MT5 ou CSV generique).

Le fuseau horaire est TOUJOURS explicite : les exports MT5 sont en heure
serveur du broker (pas en UTC). On convertit en UTC avec le fuseau IANA donne
par l'utilisateur. Aucun defaut silencieux.

Formats geres :
- Export MT5 (Historique -> Exporter) : colonnes <DATE> <TIME> <OPEN> <HIGH>
  <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>, separateur tabulation ou virgule.
  En D1, la colonne <TIME> peut etre absente.
- CSV generique : colonne `timestamp`/`time`/`datetime` + open, high, low,
  close, et optionnellement volume, spread.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

_RENAME = {
    "<date>": "date",
    "<time>": "time",
    "<open>": "open",
    "<high>": "high",
    "<low>": "low",
    "<close>": "close",
    "<tickvol>": "tick_volume",
    "<vol>": "real_volume",
    "<spread>": "spread",
}
_TS_NAMES = ("timestamp", "time", "datetime", "date")


class ImportError_(ValueError):
    """Erreur d'import (format ou fuseau)."""


def read_history_csv(
    path: str | Path,
    server_tz: str,
    ambiguous: Literal["raise", "infer"] = "raise",
) -> pd.DataFrame:
    """Lit un fichier d'historique et renvoie un DataFrame normalise en UTC.

    Colonnes de sortie : timestamp (UTC), open, high, low, close, et si presents
    volume (tick volume), spread. Les lignes sont conservees telles quelles
    (aucun nettoyage ici : voir `cleaning.clean_ohlcv`).

    `server_tz` : fuseau IANA de l'heure du fichier (ex. "UTC", "Etc/GMT-2",
    "Europe/Athens"). Les heures ambigues/inexistantes (changement d'heure)
    levent une erreur, sauf `ambiguous="infer"` pour les heures ambigues.
    Limite : "infer" exige que les deux occurrences de l'heure repetee soient
    presentes, dans l'ordre, dans le fichier (cas d'un export complet).
    """
    path = Path(path)
    sep = _sniff_sep(path)
    raw = pd.read_csv(path, sep=sep, dtype=str)
    raw.columns = [c.strip().lower() for c in raw.columns]
    raw = raw.rename(columns=_RENAME)

    naive = _build_naive_timestamp(raw)
    try:
        ts = naive.dt.tz_localize(server_tz, ambiguous=ambiguous, nonexistent="raise")
    except Exception as exc:  # pytz/zoneinfo : message explicite pour l'utilisateur
        raise ImportError_(
            f"conversion de fuseau impossible ({server_tz}): {exc}. "
            "Verifie le fuseau du broker ou utilise ambiguous='infer'."
        ) from exc

    out = pd.DataFrame({"timestamp": ts.dt.tz_convert("UTC")})
    for col in ("open", "high", "low", "close"):
        if col not in raw.columns:
            raise ImportError_(f"colonne '{col}' absente du fichier {path.name}")
        out[col] = pd.to_numeric(raw[col], errors="coerce")
    vol = "tick_volume" if "tick_volume" in raw.columns else ("volume" if "volume" in raw.columns else None)
    if vol:
        out["volume"] = pd.to_numeric(raw[vol], errors="coerce")
    if "spread" in raw.columns:
        out["spread"] = pd.to_numeric(raw["spread"], errors="coerce")
    return out


def _sniff_sep(path: Path) -> str:
    with open(path, "r", encoding="utf-8-sig") as fh:
        head = fh.readline()
    if "\t" in head:
        return "\t"
    if ";" in head and "," not in head:
        return ";"
    return ","


def _build_naive_timestamp(raw: pd.DataFrame) -> pd.Series:
    if "date" in raw.columns and "time" in raw.columns:
        txt = raw["date"].str.strip() + " " + raw["time"].str.strip()
    elif "date" in raw.columns and not any(n in raw.columns for n in ("timestamp", "datetime")):
        txt = raw["date"].str.strip()  # D1 MT5 sans heure
    else:
        name = next((n for n in ("timestamp", "datetime", "time", "date") if n in raw.columns), None)
        if name is None:
            raise ImportError_(f"aucune colonne d'horodatage parmi {_TS_NAMES}")
        txt = raw[name].str.strip()
    ts = pd.to_datetime(txt, errors="coerce", format="mixed")
    if ts.isna().any():
        raise ImportError_(f"{int(ts.isna().sum())} horodatage(s) illisible(s)")
    if getattr(ts.dt, "tz", None) is not None:
        raise ImportError_("le fichier contient deja des fuseaux : fournir des heures naives + server_tz")
    return ts
