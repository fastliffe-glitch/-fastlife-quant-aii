from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from fastlife_quant.data import Candle, DataKind, DataSource, Timeframe, ValidationStatus


def make(**over):
    base = dict(
        timestamp=datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc),
        timeframe=Timeframe.M5,
        source=DataSource.TEST_FIXTURE,
        kind=DataKind.SIMULATED,
        open=2000.0,
        high=2002.0,
        low=1999.0,
        close=2001.0,
    )
    base.update(over)
    return Candle(**base)


def test_valid_candle_defaults_to_unvalidated():
    c = make()
    assert c.status is ValidationStatus.UNVALIDATED
    assert c.kind is DataKind.SIMULATED


def test_naive_timestamp_rejected():
    with pytest.raises(ValidationError):
        make(timestamp=datetime(2026, 1, 5, 10, 0))


def test_timestamp_converted_to_utc():
    paris = timezone(timedelta(hours=1))
    c = make(timestamp=datetime(2026, 1, 5, 11, 0, tzinfo=paris))
    assert c.timestamp == datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "over",
    [
        dict(high=1998.0),  # high sous le low
        dict(low=2005.0),  # low au-dessus du high
        dict(open=0.0),
        dict(close=-1.0),
        dict(volume=-5.0),
        dict(spread=-0.1),
    ],
)
def test_inconsistent_candle_rejected(over):
    with pytest.raises(ValidationError):
        make(**over)


def test_timeframe_seconds():
    assert Timeframe.M5.seconds == 300
    assert Timeframe.M15.seconds == 900
    assert Timeframe.H1.seconds == 3600
    assert Timeframe.H4.seconds == 14400
    assert Timeframe.D1.seconds == 86400
