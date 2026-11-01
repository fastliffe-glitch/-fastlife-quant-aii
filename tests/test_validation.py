"""Tests du validateur OHLCV.

Les series ci-dessous sont des FIXTURES DE TEST deterministes, jamais des
donnees de marche. Elles servent uniquement a verifier la logique.
"""

import numpy as np
import pandas as pd
import pytest

from fastlife_quant.data import (
    DataKind,
    DataSource,
    SeriesMetadata,
    Timeframe,
    ValidationStatus,
    validate_ohlcv,
    validate_series,
)


def fixture_df(n=20, start="2026-01-05 00:00", freq="5min"):  # lundi
    ts = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    close = 2000.0 + np.arange(n) * 0.1
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": close - 0.05,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 10.0),
            "spread": np.full(n, 0.2),
        }
    )


def test_clean_series_is_valid():
    r = validate_ohlcv(fixture_df(), Timeframe.M5)
    assert r.status is ValidationStatus.VALID
    assert r.issues == []


def test_input_is_not_mutated():
    df = fixture_df()
    before = df.copy(deep=True)
    validate_ohlcv(df.drop(index=[3, 4]), Timeframe.M5)
    pd.testing.assert_frame_equal(df, before)


def test_missing_columns():
    r = validate_ohlcv(fixture_df().drop(columns=["close"]), Timeframe.M5)
    assert r.has("missing_columns")
    assert r.status is ValidationStatus.INVALID


def test_empty_series():
    r = validate_ohlcv(fixture_df().iloc[0:0], Timeframe.M5)
    assert r.has("empty")


def test_naive_timestamps_rejected():
    df = fixture_df()
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    assert validate_ohlcv(df, Timeframe.M5).has("timestamp_not_tz_aware")


def test_non_utc_timestamps_rejected():
    df = fixture_df()
    df["timestamp"] = df["timestamp"].dt.tz_convert("Europe/Paris")
    assert validate_ohlcv(df, Timeframe.M5).has("timestamp_not_utc")


def test_duplicates_detected():
    df = pd.concat([fixture_df(), fixture_df().iloc[[5]]]).sort_values("timestamp")
    assert validate_ohlcv(df, Timeframe.M5).has("duplicate_timestamps")


def test_unsorted_detected():
    df = fixture_df().iloc[::-1].reset_index(drop=True)
    assert validate_ohlcv(df, Timeframe.M5).has("not_sorted")


def test_nan_prices_detected_and_not_filled():
    df = fixture_df()
    df.loc[4, "close"] = np.nan
    r = validate_ohlcv(df, Timeframe.M5)
    assert r.has("price_nan")
    assert df["close"].isna().sum() == 1  # jamais comble


def test_non_positive_price():
    df = fixture_df()
    df.loc[2, "low"] = 0.0
    assert validate_ohlcv(df, Timeframe.M5).has("price_non_positive")


def test_ohlc_inconsistent():
    df = fixture_df()
    df.loc[7, "high"] = df.loc[7, "low"] - 1
    r = validate_ohlcv(df, Timeframe.M5)
    assert r.has("ohlc_inconsistent")
    assert r.status is ValidationStatus.INVALID


def test_negative_volume_and_spread():
    df = fixture_df()
    df.loc[1, "volume"] = -1
    df.loc[2, "spread"] = -0.5
    r = validate_ohlcv(df, Timeframe.M5)
    assert r.has("volume_negative") and r.has("spread_negative")


def test_unexpected_gap_is_warning_and_not_filled():
    df = fixture_df().drop(index=[5, 6, 7]).reset_index(drop=True)
    r = validate_ohlcv(df, Timeframe.M5)
    assert r.status is ValidationStatus.VALID_WITH_WARNINGS
    gap = next(i for i in r.issues if i.code == "unexpected_gaps")
    assert gap.count == 1
    assert "3 bougies" in gap.message
    assert len(df) == 17  # aucune ligne ajoutee


def test_weekend_gap_is_expected():
    # vendredi 21:55 UTC -> dimanche 23:00 UTC
    ts = pd.DatetimeIndex(
        ["2026-01-09 21:50", "2026-01-09 21:55", "2026-01-11 23:00", "2026-01-11 23:05"], tz="UTC"
    )
    df = fixture_df(4)
    df["timestamp"] = ts
    r = validate_ohlcv(df, Timeframe.M5)
    assert r.status is ValidationStatus.VALID
    assert r.expected_gaps == 1


def test_midweek_gap_is_not_weekend():
    ts = pd.DatetimeIndex(["2026-01-07 10:00", "2026-01-08 10:00"], tz="UTC")
    df = fixture_df(2)
    df["timestamp"] = ts
    assert validate_ohlcv(df, Timeframe.H1).has("unexpected_gaps")


def test_daily_weekend_gap_expected():
    ts = pd.DatetimeIndex(["2026-01-08", "2026-01-09", "2026-01-12"], tz="UTC")  # jeu, ven, lun
    df = fixture_df(3)
    df["timestamp"] = ts
    r = validate_ohlcv(df, Timeframe.D1)
    assert r.status is ValidationStatus.VALID


def test_validate_series_updates_status_without_mutating_input_metadata():
    meta = SeriesMetadata(timeframe=Timeframe.M5, source=DataSource.TEST_FIXTURE, kind=DataKind.SIMULATED)
    out = validate_series(fixture_df(), meta)
    assert out.metadata.status is ValidationStatus.VALID
    assert meta.status is ValidationStatus.UNVALIDATED

    bad = fixture_df().drop(columns=["open"])
    assert validate_series(bad, meta).metadata.status is ValidationStatus.INVALID


@pytest.mark.parametrize("tf", list(Timeframe))
def test_all_timeframes_clean(tf):
    df = fixture_df(10, freq=f"{tf.seconds}s")
    assert validate_ohlcv(df, tf).status is ValidationStatus.VALID
