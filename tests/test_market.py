"""Tests Phase 2. Toutes les series sont des FIXTURES synthetiques deterministes
(jamais des donnees de marche reelles)."""

import json

import numpy as np
import pandas as pd
import pytest

from fastlife_quant.data import DataKind, DataSource, Timeframe, ValidationStatus
from fastlife_quant.market import (
    SessionConfig,
    clean_ohlcv,
    import_history,
    load_processed,
    read_history_csv,
    resample_ohlcv,
    tag_sessions,
)
from fastlife_quant.market.importers import ImportError_


def make_df(n=12, start="2026-01-05 00:00", freq="5min"):
    ts = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    close = 2000.0 + np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(n, 10.0),
            "spread": np.full(n, 0.2),
        }
    )


def write_mt5(path, rows, header="<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>"):
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


# ---------- importers ----------

def test_read_mt5_export_converts_server_time_to_utc(tmp_path):
    f = tmp_path / "XAUUSD_M5.csv"
    write_mt5(f, ["2026.01.05\t02:00:00\t2000.0\t2001.0\t1999.0\t2000.5\t100\t0\t20"])
    df = read_history_csv(f, server_tz="Etc/GMT-2")  # UTC+2
    assert df["timestamp"].iloc[0] == pd.Timestamp("2026-01-05 00:00", tz="UTC")
    assert df["volume"].iloc[0] == 100
    assert df["spread"].iloc[0] == 20


def test_read_generic_csv_with_dst_timezone(tmp_path):
    f = tmp_path / "gen.csv"
    f.write_text(
        "timestamp,open,high,low,close\n"
        "2026-01-05 12:00:00,1,2,0.5,1.5\n"
        "2026-07-06 12:00:00,1,2,0.5,1.5\n"
    )
    df = read_history_csv(f, server_tz="Europe/Athens")
    assert df["timestamp"].iloc[0] == pd.Timestamp("2026-01-05 10:00", tz="UTC")  # UTC+2 hiver
    assert df["timestamp"].iloc[1] == pd.Timestamp("2026-07-06 09:00", tz="UTC")  # UTC+3 ete


def test_d1_mt5_without_time_column(tmp_path):
    f = tmp_path / "d1.csv"
    write_mt5(f, ["2026.01.05\t2000\t2010\t1990\t2005\t5000\t0\t20"], header="<DATE>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>")
    df = read_history_csv(f, server_tz="UTC")
    assert df["timestamp"].iloc[0] == pd.Timestamp("2026-01-05", tz="UTC")


def test_ambiguous_dst_hour_raises_then_infer(tmp_path):
    f = tmp_path / "amb.csv"
    # 03:30 apparait deux fois (retour a l'heure d'hiver) : cas d'un vrai export
    f.write_text("timestamp,open,high,low,close\n2026-10-25 03:30:00,1,2,0.5,1.5\n2026-10-25 03:30:00,1,2,0.5,1.6\n")
    with pytest.raises(ImportError_):
        read_history_csv(f, server_tz="Europe/Athens")
    df = read_history_csv(f, server_tz="Europe/Athens", ambiguous="infer")
    assert list(df["timestamp"]) == [
        pd.Timestamp("2026-10-25 00:30", tz="UTC"),  # 1re occurrence : heure d'ete (UTC+3)
        pd.Timestamp("2026-10-25 01:30", tz="UTC"),  # 2e occurrence : heure d'hiver (UTC+2)
    ]


def test_missing_price_column_and_bad_timestamp(tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("timestamp,open,high,low\n2026-01-05 00:00:00,1,2,0.5\n")
    with pytest.raises(ImportError_):
        read_history_csv(f, server_tz="UTC")
    g = tmp_path / "bad2.csv"
    g.write_text("timestamp,open,high,low,close\nnot-a-date,1,2,0.5,1\n")
    with pytest.raises(ImportError_):
        read_history_csv(g, server_tz="UTC")


# ---------- cleaning ----------

def test_exact_duplicate_dropped_and_logged():
    df = pd.concat([make_df(), make_df().iloc[[4]]]).sort_values("timestamp", kind="stable")
    r = clean_ohlcv(df, Timeframe.M5)
    assert r.n_exact_duplicates_dropped == 1
    assert len(r.clean) == 12
    assert r.report.status is ValidationStatus.VALID


def test_conflicting_duplicates_quarantined_not_chosen():
    df = make_df()
    dup = df.iloc[[4]].copy()
    dup["close"] = dup["close"] + 0.3
    dup["high"] = dup["high"] + 0.3
    r = clean_ohlcv(pd.concat([df, dup]).sort_values("timestamp", kind="stable"), Timeframe.M5)
    assert r.n_conflicting_rows == 2
    assert len(r.clean) == 11  # aucune des deux versions conservee
    assert (r.quarantine["reason"] == "conflicting_duplicate").sum() == 2


def test_invalid_rows_quarantined_with_reason():
    df = make_df()
    df.loc[2, "close"] = np.nan
    df.loc[3, "low"] = 0.0
    df.loc[6, "high"] = df.loc[6, "low"] - 5
    r = clean_ohlcv(df, Timeframe.M5)
    assert set(r.quarantine["reason"]) == {"price_nan", "price_non_positive", "ohlc_inconsistent"}
    assert len(r.clean) == 9


def test_resort_only_and_no_fabrication():
    df = make_df().iloc[::-1].reset_index(drop=True).drop(index=[3])
    r = clean_ohlcv(df, Timeframe.M5)
    assert r.was_resorted
    assert r.clean["timestamp"].is_monotonic_increasing
    assert len(r.clean) == len(df)  # trou conserve, rien ajoute
    assert r.report.has("unexpected_gaps")


# ---------- timeframes ----------

def test_resample_m5_to_m15_values():
    r = resample_ohlcv(make_df(6), Timeframe.M5, Timeframe.M15)
    d = r.data
    assert len(d) == 2
    first = d.iloc[0]
    assert first["open"] == 1999.5 and first["close"] == 2002.0
    assert first["high"] == 2003.0 and first["low"] == 1999.0
    assert first["volume"] == 30.0 and first["n_bars"] == 3 and first["coverage"] == 1.0


def test_resample_drops_incomplete_bucket_without_fabricating():
    df = make_df(6).drop(index=[1])  # le premier bucket M15 n'a que 2 bougies
    r = resample_ohlcv(df, Timeframe.M5, Timeframe.M15, min_coverage=1.0)
    assert r.n_buckets_dropped_low_coverage == 1
    assert len(r.data) == 1
    r2 = resample_ohlcv(df, Timeframe.M5, Timeframe.M15, min_coverage=0.6)
    assert len(r2.data) == 2 and r2.data.iloc[0]["coverage"] == pytest.approx(2 / 3)


def test_resample_h1_to_h4_and_anchor():
    h1 = make_df(8, start="2026-01-05 00:00", freq="1h")
    d = resample_ohlcv(h1, Timeframe.H1, Timeframe.H4).data
    assert list(d["timestamp"]) == [pd.Timestamp("2026-01-05 00:00", tz="UTC"), pd.Timestamp("2026-01-05 04:00", tz="UTC")]
    a = resample_ohlcv(make_df(8, start="2026-01-05 02:00", freq="1h"), Timeframe.H1, Timeframe.H4, anchor=pd.Timedelta(hours=2)).data
    assert a.iloc[0]["timestamp"] == pd.Timestamp("2026-01-05 02:00", tz="UTC")
    assert len(a) == 2


def test_resample_rejects_bad_inputs():
    with pytest.raises(ValueError):
        resample_ohlcv(make_df(), Timeframe.H1, Timeframe.M15)
    with pytest.raises(ValueError):
        resample_ohlcv(make_df().iloc[::-1], Timeframe.M5, Timeframe.M15)


def test_resample_does_not_mutate_input():
    df = make_df(6)
    before = df.copy(deep=True)
    resample_ohlcv(df, Timeframe.M5, Timeframe.M15)
    pd.testing.assert_frame_equal(df, before)


# ---------- sessions ----------

def test_session_tags():
    ts = pd.Series(pd.to_datetime(["2026-01-05 03:00", "2026-01-05 09:00", "2026-01-05 15:00", "2026-01-05 22:00"], utc=True))
    assert list(tag_sessions(ts)) == ["ASIA", "LONDON", "NEWYORK", "OFF"]
    custom = SessionConfig(windows=(("X", 0, 24),))
    assert set(tag_sessions(ts, custom)) == {"X"}
    with pytest.raises(ValueError):
        tag_sessions(pd.Series(pd.to_datetime(["2026-01-05 03:00"])))


# ---------- pipeline ----------

def test_pipeline_preserves_raw_and_writes_provenance(tmp_path):
    src = tmp_path / "in" / "XAUUSD_M5.csv"
    src.parent.mkdir()
    rows = [f"2026.01.05\t{h:02d}:{m:02d}:00\t2000\t2001\t1999\t2000.5\t10\t0\t20" for h in (2,) for m in (0, 5, 10)]
    rows.append(rows[1])  # doublon exact
    write_mt5(src, rows)
    original = src.read_bytes()

    res = import_history(
        src, Timeframe.M5, "Etc/GMT-2", DataSource.TEST_FIXTURE, DataKind.SIMULATED,
        raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed",
    )
    assert src.read_bytes() == original
    assert res.raw_path.read_bytes() == original
    meta = json.loads(res.meta_path.read_text())
    assert meta["kind"] == "simulated" and meta["server_tz"] == "Etc/GMT-2"
    assert meta["rows_input"] == 4 and meta["rows_clean"] == 3
    assert meta["exact_duplicates_dropped"] == 1 and meta["validation_status"] == "valid"

    back = load_processed(res.processed_path)
    assert back["timestamp"].iloc[0] == pd.Timestamp("2026-01-05 00:00", tz="UTC")

    again = import_history(
        src, Timeframe.M5, "Etc/GMT-2", DataSource.TEST_FIXTURE, DataKind.SIMULATED,
        raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed",
    )
    assert again.raw_path == res.raw_path  # idempotent
    assert len(list((tmp_path / "raw").iterdir())) == 1


def test_pipeline_writes_quarantine_file(tmp_path):
    src = tmp_path / "q.csv"
    write_mt5(src, [
        "2026.01.05\t02:00:00\t2000\t2001\t1999\t2000.5\t10\t0\t20",
        "2026.01.05\t02:05:00\t2000\t1990\t1999\t2000.5\t10\t0\t20",  # high < low
    ])
    res = import_history(src, Timeframe.M5, "UTC", DataSource.TEST_FIXTURE, DataKind.SIMULATED, tmp_path / "raw", tmp_path / "p")
    assert (tmp_path / "p").glob("*.quarantine.csv")
    assert json.loads(res.meta_path.read_text())["rows_quarantined"] == 1
