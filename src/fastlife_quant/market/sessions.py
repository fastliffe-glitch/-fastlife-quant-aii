"""Etiquetage des sessions de marche (fenetres UTC fixes et configurables).

Les fenetres par defaut sont une approximation FIXE en UTC : elles ne suivent
pas les changements d'heure d'ete/hiver. A ajuster dans `SessionConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SessionConfig:
    # (nom, heure de debut incluse, heure de fin exclue), en heures UTC
    windows: tuple[tuple[str, int, int], ...] = (
        ("ASIA", 0, 7),
        ("LONDON", 7, 12),
        ("NEWYORK", 12, 21),
    )
    other: str = "OFF"


def tag_sessions(timestamps: pd.Series, config: SessionConfig = SessionConfig()) -> pd.Series:
    if not isinstance(timestamps.dtype, pd.DatetimeTZDtype) or str(timestamps.dt.tz) != "UTC":
        raise ValueError("timestamps doit etre tz-aware UTC")
    hours = timestamps.dt.hour
    out = pd.Series(config.other, index=timestamps.index, dtype=object)
    for name, start, end in config.windows:
        out[(hours >= start) & (hours < end)] = name
    return out
