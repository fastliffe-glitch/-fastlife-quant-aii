import random
from datetime import datetime, timezone

import pytest

from fastlife_quant.risk.v2 import (
    AccountSnapshot,
    InstrumentSpec,
    RiskEngineV2,
)


# --------------------------------------------------------------------------- #
# Helpers
#
# Default trade: buy at 100, stop 90, target 120 on an instrument where one
# price unit is one tick worth 10 USD per lot:
#   stop   = 10 ticks = 100 USD / lot
#   reward = 20 ticks = 200 USD / lot  (net RR = 2.0, the minimum accepted)
# Default account: 10 000 USD, 1 % risk per trade -> 100 USD budget -> 1.00 lot.
# --------------------------------------------------------------------------- #


def make_instrument(**overrides):
    values = {
        "symbol": "TEST",
        "contract_size": 1,
        "tick_size": 1,
        "tick_value_per_lot": 10,
        "volume_min": 0.01,
        "volume_max": 100,
        "volume_step": 0.01,
        "leverage": 100,
        "account_currency": "USD",
    }
    values.update(overrides)
    return InstrumentSpec(**values)


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


def make_engine(**overrides):
    values = {"margin_provider": lambda *args: 10}
    values.update(overrides)
    return RiskEngineV2(**values)


def evaluate(engine, snapshot=None, instrument=None, **trade):
    params = {"symbol": "TEST", "side": 1, "entry": 100, "stop_loss": 90, "take_profit": 120}
    params.update(trade)
    return engine.evaluate_trade(
        instrument=instrument if instrument is not None else make_instrument(),
        snapshot=snapshot if snapshot is not None else make_snapshot(),
        **params,
    )


# --------------------------------------------------------------------------- #
# Existing regression tests
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# 1. Daily loss: blocked at exactly -3 %
# --------------------------------------------------------------------------- #


def test_daily_loss_blocks_at_exactly_minus_3_percent():
    # -3 % of a 10 000 balance is -300.
    decision = evaluate(make_engine(), make_snapshot(daily_pnl=-300))

    assert decision.allowed is False
    assert decision.reason == "daily loss limit reached"


def test_daily_loss_just_inside_the_limit_is_allowed():
    decision = evaluate(make_engine(), make_snapshot(daily_pnl=-299.99))

    assert decision.allowed is True


@pytest.mark.parametrize("balance", [1000.0, 2500.5, 10000.0, 24469.19, 89565.28, 397601.1])
def test_daily_loss_blocks_at_exactly_minus_3_percent_for_any_balance(balance):
    # The P&L is computed differently from the engine's threshold on purpose:
    # for several of these balances the two differ by ~1e-13 in binary floats,
    # which used to let a trade through exactly at the limit.
    daily_pnl = -(balance * 3 / 100)
    snapshot = make_snapshot(balance=balance, equity=balance, peak_equity=balance, daily_pnl=daily_pnl)

    decision = evaluate(make_engine(), snapshot)

    assert decision.allowed is False
    assert decision.reason == "daily loss limit reached"


def test_daily_profit_never_triggers_the_daily_loss_limit():
    decision = evaluate(make_engine(), make_snapshot(daily_pnl=500))

    assert decision.allowed is True


# --------------------------------------------------------------------------- #
# 2. Drawdown: blocked at exactly 20 %
# --------------------------------------------------------------------------- #


def test_drawdown_blocks_at_exactly_20_percent():
    decision = evaluate(make_engine(), make_snapshot(equity=8000, peak_equity=10000))

    assert decision.allowed is False
    assert decision.reason == "drawdown limit reached"


def test_drawdown_just_inside_the_limit_is_allowed():
    decision = evaluate(make_engine(), make_snapshot(equity=8000.01, peak_equity=10000))

    assert decision.allowed is True


@pytest.mark.parametrize("peak", [10000.0, 75509.5, 161984.0, 325502.14])
def test_drawdown_blocks_at_exactly_20_percent_for_any_peak(peak):
    # equity = peak * 0.8 carries float error (e.g. 129587.20000000001), which
    # makes (peak - equity) / peak come out as 0.19999999999999993 < 0.20.
    equity = peak * 0.8
    snapshot = make_snapshot(balance=equity, equity=equity, peak_equity=peak)

    decision = evaluate(make_engine(), snapshot)

    assert decision.allowed is False
    assert decision.reason == "drawdown limit reached"


# --------------------------------------------------------------------------- #
# 3. Spread
# --------------------------------------------------------------------------- #


def test_spread_cost_per_lot_conversion():
    engine = make_engine()

    # 0.5 price units / 0.25 tick size = 2 ticks, 2 ticks * 2.5 per tick = 5.0
    instrument = make_instrument(tick_size=0.25, tick_value_per_lot=2.5, spread=0.5)
    assert engine._spread_cost_per_lot(instrument) == pytest.approx(5.0)

    assert engine._spread_cost_per_lot(make_instrument(spread=0)) == 0.0


def test_spread_is_added_to_risk_and_subtracted_from_reward():
    # spread 2 price units = 2 ticks = 20 USD / lot
    decision = evaluate(make_engine(), instrument=make_instrument(spread=2), take_profit=130)

    assert decision.allowed is True
    assert decision.metadata["risk_per_lot"] == pytest.approx(120)  # 100 stop + 20 spread
    assert decision.metadata["reward_per_lot"] == pytest.approx(280)  # 300 target - 20 spread
    assert decision.risk_reward == pytest.approx(280 / 120)
    assert decision.volume == pytest.approx(0.83)  # 100 / 120 = 0.8333 -> 0.83


def test_spread_can_push_net_rr_below_the_minimum():
    # Gross RR is exactly 2.0, but a 20 USD spread makes it 180 / 120 = 1.5.
    decision = evaluate(make_engine(), instrument=make_instrument(spread=2))

    assert decision.allowed is False
    assert decision.reason == "net RR after costs < 2.0"
    assert decision.risk_reward == pytest.approx(1.5)


# --------------------------------------------------------------------------- #
# 4. Commissions (and no double counting with the spread)
# --------------------------------------------------------------------------- #


def test_commission_is_added_to_risk_and_subtracted_from_reward():
    instrument = make_instrument(round_trip_cost_per_lot=7)

    decision = evaluate(make_engine(), instrument=instrument, take_profit=125)

    assert decision.allowed is True
    assert decision.metadata["risk_per_lot"] == pytest.approx(107)  # 100 stop + 7 commission
    assert decision.metadata["reward_per_lot"] == pytest.approx(243)  # 250 target - 7 commission
    assert decision.risk_reward == pytest.approx(243 / 107)
    assert decision.volume == pytest.approx(0.93)  # 100 / 107 = 0.9346 -> 0.93
    assert decision.risk_per_trade == pytest.approx(0.93 * 107)


def test_spread_is_not_counted_twice_with_round_trip_cost_per_lot():
    engine = make_engine()

    def per_lot(**costs):
        decision = evaluate(engine, instrument=make_instrument(**costs), take_profit=140)
        assert decision.allowed is True
        return decision.metadata["risk_per_lot"], decision.metadata["reward_per_lot"]

    base_risk, base_reward = per_lot()
    assert (base_risk, base_reward) == (pytest.approx(100), pytest.approx(400))

    spread_risk, spread_reward = per_lot(spread=2)  # +20 USD / lot
    commission_risk, commission_reward = per_lot(round_trip_cost_per_lot=7)  # +7 USD / lot
    both_risk, both_reward = per_lot(spread=2, round_trip_cost_per_lot=7)

    # Each cost is charged once on its own...
    assert spread_risk == pytest.approx(base_risk + 20)
    assert commission_risk == pytest.approx(base_risk + 7)
    # ...and together they simply add up: spread counted once, commission once.
    assert both_risk == pytest.approx(base_risk + 20 + 7)
    assert both_reward == pytest.approx(base_reward - 20 - 7)
    assert spread_reward == pytest.approx(base_reward - 20)
    assert commission_reward == pytest.approx(base_reward - 7)


# --------------------------------------------------------------------------- #
# 5. Volume rounding
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "volume, step, expected",
    [
        (0.8333333333, 0.01, 0.83),
        (0.29, 0.01, 0.29),  # 0.29 / 0.01 == 28.999999999999996 in binary floats
        (1.15, 0.05, 1.15),  # 1.15 / 0.05 == 22.999999999999996 in binary floats
        (0.99, 0.1, 0.9),
        (2.5, 1.0, 2.0),
        (0.009, 0.01, 0.0),
    ],
)
def test_round_down_volume_rounds_down_without_float_artifacts(volume, step, expected):
    engine = make_engine()

    assert engine._round_down_volume(volume, make_instrument(volume_step=step)) == expected


def test_volume_rounding_does_not_lose_a_step_to_float_error():
    # budget = 2900 * 1 % = 29 USD, risk 100 USD / lot -> exactly 0.29 lot.
    snapshot = make_snapshot(balance=2900, equity=2900, peak_equity=2900)

    decision = evaluate(make_engine(), snapshot)

    assert decision.allowed is True
    assert decision.volume == 0.29


def test_volume_is_never_rounded_up_past_the_risk_budget():
    # risk 120 USD / lot -> raw 0.8333 lot; 0.84 would risk 100.80 > 100 budget.
    decision = evaluate(make_engine(), instrument=make_instrument(spread=2), take_profit=130)

    assert decision.volume == 0.83
    assert decision.risk_per_trade <= 10000 * 0.01


# --------------------------------------------------------------------------- #
# 6. Refusal when the risk budget is exceeded
# --------------------------------------------------------------------------- #


def test_trade_refused_when_budget_cannot_cover_the_minimum_volume():
    # budget = 50 * 1 % = 0.50 USD, but one minimum lot (0.01) risks 1.00 USD.
    snapshot = make_snapshot(balance=50, equity=50, peak_equity=50)

    decision = evaluate(make_engine(), snapshot)

    assert decision.allowed is False
    assert decision.reason == "requested volume is below broker minimum"
    assert decision.risk_per_trade == pytest.approx(0.5)


def test_trade_refused_when_rounding_would_exceed_the_risk_budget(monkeypatch):
    # Safety net: even if the rounding step were faulty and rounded UP
    # (0.84 lot * 120 USD = 100.80 USD > 100 USD budget), the trade is refused.
    monkeypatch.setattr(RiskEngineV2, "_round_down_volume", lambda self, volume, instrument: 0.84)

    decision = evaluate(make_engine(), instrument=make_instrument(spread=2), take_profit=130)

    assert decision.allowed is False
    assert decision.reason == "risk budget exceeded after volume rounding"
    assert decision.risk_per_trade == pytest.approx(0.84 * 120)


def test_accepted_trades_never_risk_more_than_the_budget():
    rng = random.Random(20261101)
    engine = make_engine()
    accepted = 0

    for _ in range(300):
        equity = round(rng.uniform(500, 250000), 2)
        instrument = make_instrument(
            spread=round(rng.uniform(0, 3), 2),
            round_trip_cost_per_lot=round(rng.uniform(0, 12), 2),
            volume_step=rng.choice([0.01, 0.05, 0.1]),
        )
        snapshot = make_snapshot(balance=equity, equity=equity, peak_equity=equity)

        decision = evaluate(engine, snapshot, instrument, stop_loss=90, take_profit=150)

        if decision.allowed:
            accepted += 1
            assert decision.risk_per_trade <= equity * 0.01 + 1e-9

    assert accepted > 0
