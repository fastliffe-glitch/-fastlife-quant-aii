from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class DataSourceConfig:
    path: str | None = None
    timeframe: str = "M5"
    symbol: str = "XAUUSD"
    source: str = "csv"


class HistoricalDataLoader:
    """Chargeur de donnees historiques XAUUSD depuis fichier CSV ou export MT5.

    Cette couche est conforme au principe de source verifiable; elle ne fabrique pas
    les donnees, elle les normalise seulement.
    """

    def __init__(self, source: DataSourceConfig | None = None) -> None:
        self.source = source or DataSourceConfig()

    def load_csv(self, path: str | None = None) -> pd.DataFrame:
        csv_path = path or self.source.path
        if csv_path is None:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        df = pd.read_csv(csv_path)
        return self.normalize(df)

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized = df.copy()
        if "timestamp" in normalized.columns:
            normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], errors="coerce")
        for column in ["open", "high", "low", "close", "volume"]:
            if column in normalized.columns:
                normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        if "symbol" not in normalized.columns:
            normalized["symbol"] = self.source.symbol
        if "timeframe" not in normalized.columns:
            normalized["timeframe"] = self.source.timeframe
        return normalized.dropna(subset=["timestamp"]).reset_index(drop=True)


__all__ = ["DataSourceConfig", "HistoricalDataLoader"]
