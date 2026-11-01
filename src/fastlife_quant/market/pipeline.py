"""Pipeline d'import : archive brute -> lecture -> nettoyage -> validation -> sortie.

Le fichier d'origine est copie tel quel dans data/raw (nom prefixe par son
SHA-256) et n'est jamais modifie. La sortie nettoyee va dans data/processed
avec un fichier de provenance (.meta.json) : source, nature (real/simulated),
fuseau d'origine, statut de validation et compteurs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from fastlife_quant.data import DataKind, DataSource, Timeframe
from fastlife_quant.market.cleaning import CleaningResult, clean_ohlcv
from fastlife_quant.market.importers import read_history_csv


@dataclass
class ImportResult:
    raw_path: Path
    processed_path: Path
    meta_path: Path
    cleaning: CleaningResult


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_raw(src: Path, raw_dir: Path) -> tuple[Path, str]:
    """Copie le fichier d'origine dans raw_dir (idempotent, jamais ecrase)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    digest = sha256_file(src)
    dest = raw_dir / f"{digest[:12]}_{src.name}"
    if not dest.exists():
        shutil.copy2(src, dest)
    return dest, digest


def import_history(
    src: str | Path,
    timeframe: Timeframe,
    server_tz: str,
    source: DataSource,
    kind: DataKind,
    raw_dir: str | Path,
    processed_dir: str | Path,
    symbol: str = "XAUUSD",
    ambiguous: str = "raise",
) -> ImportResult:
    """`kind` est explicite : REAL pour un export de marche, SIMULATED sinon."""
    src = Path(src)
    raw_dir, processed_dir = Path(raw_dir), Path(processed_dir)
    raw_path, digest = archive_raw(src, raw_dir)

    df = read_history_csv(raw_path, server_tz=server_tz, ambiguous=ambiguous)  # type: ignore[arg-type]
    res = clean_ohlcv(df, timeframe)

    processed_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{symbol}_{timeframe.value}_{digest[:12]}"
    out_csv = processed_dir / f"{stem}.csv"
    res.clean.to_csv(out_csv, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    if len(res.quarantine):
        res.quarantine.to_csv(processed_dir / f"{stem}.quarantine.csv", index=False)

    meta = {
        "symbol": symbol,
        "timeframe": timeframe.value,
        "source": source.value,
        "kind": kind.value,
        "original_file": src.name,
        "raw_archive": str(raw_path),
        "sha256": digest,
        "server_tz": server_tz,
        "timezone_output": "UTC",
        "imported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "validation_status": res.report.status.value,
        "rows_input": res.n_input,
        "rows_clean": len(res.clean),
        "rows_quarantined": len(res.quarantine),
        "exact_duplicates_dropped": res.n_exact_duplicates_dropped,
        "conflicting_rows": res.n_conflicting_rows,
        "resorted": res.was_resorted,
        "issues": [
            {"severity": i.severity.value, "code": i.code, "message": i.message, "count": i.count}
            for i in res.report.issues
        ],
    }
    meta_path = processed_dir / f"{stem}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return ImportResult(raw_path, out_csv, meta_path, res)


def load_processed(csv_path: str | Path) -> pd.DataFrame:
    """Recharge une sortie nettoyee (timestamps UTC)."""
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df
