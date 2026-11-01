from datetime import datetime, timezone

from fastlife_quant.risk.v2 import (
    AccountSnapshot,
    InstrumentSpec,
    RiskEngineV2,
)


def make_instrument():
    return InstrumentSpec(
        symbol="TEST",
        contract_size=1,
        tick_size=1,
        tick_value_per_lot=10,
        volume_min=0.01,
        volume_max=100,
        volume_step=0.01,
        leverage=100,
        account_currency="USD",
    )


def make_snapshot(**overrides):
    values = {
        "balance": 10000,
        "equity": 10000,
        "daily_pnl": 0,
        "open_exposure": 0,
        "used_margin": 0,
        "peak_equity": 10000,
        "updated_at": datetime.now(timezone.utc),
        "currency": "USD",
    }
    values.update(overrides)
    return AccountSnapshot(**values)


def evaluate(engine, snapshot):
    return engine.evaluate_trade(
        symbol="TEST",
        side=1,
        entry=100,
        stop_loss=90,
        take_profit=120,
        instrument=make_instrument(),
        snapshot=snapshot,
    )


def test_snapshot_numeric_strings_are_normalized():
    engine = RiskEngineV2(
        max_exposure_notional=1000,
        margin_provider=lambda *args: 10,
    )

    snapshot = make_snapshot(
        balance="10000",
        equity="10000",
        daily_pnl="0",
        open_exposure="0",
        used_margin="0",
        peak_equity="10000",
    )

    decision = evaluate(engine, snapshot)

    assert decision.allowed is True
    assert decision.volume == 1.0


def test_existing_exposure_is_included_in_limit():
    engine = RiskEngineV2(
        max_exposure_notional=1000,
        margin_provider=lambda *args: 10,
    )

    snapshot = make_snapshot(open_exposure=950)

    decision = evaluate(engine, snapshot)

    assert decision.allowed is False
    assert decision.reason == "exposure limit exceeded"
    assert decision.metadata["total_exposure_after_trade"] == 1050
