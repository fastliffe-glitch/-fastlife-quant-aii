from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from math import isfinite
from typing import Any, Callable, Dict, Optional, Union

NumericLike = Union[int, float, Decimal, str]


def _coerce_float(value: Any, field_name: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None

    try:
        if isinstance(value, Decimal):
            number = float(value)
        elif isinstance(value, (int, float)):
            number = float(value)
        elif isinstance(value, str):
            number = float(value)
        else:
            return None
    except (ArithmeticError, OverflowError, TypeError, ValueError, InvalidOperation):
        return None

    if not isfinite(number):
        return None
    return number


def _normalize_snapshot(snapshot: Any) -> Optional[Dict[str, Any]]:
    if snapshot is None or not isinstance(snapshot, AccountSnapshot):
        return None

    balance = _coerce_float(snapshot.balance, "balance")
    equity = _coerce_float(snapshot.equity, "equity")
    daily_pnl = _coerce_float(snapshot.daily_pnl, "daily_pnl")
    open_exposure = _coerce_float(snapshot.open_exposure, "open_exposure")
    used_margin = _coerce_float(snapshot.used_margin, "used_margin")
    peak_equity = _coerce_float(snapshot.peak_equity, "peak_equity")
    updated_at = snapshot.updated_at

    if balance is None or balance <= 0:
        return None
    if equity is None or equity <= 0:
        return None
    if daily_pnl is None:
        return None
    if open_exposure is None or open_exposure < 0:
        return None
    if used_margin is None or used_margin < 0:
        return None
    if peak_equity is None or peak_equity <= 0:
        return None
    if not isinstance(updated_at, datetime):
        return None
    if updated_at.tzinfo is None or updated_at.utcoffset() is None:
        return None

    return {
        "balance": float(balance),
        "equity": float(equity),
        "daily_pnl": float(daily_pnl),
        "open_exposure": float(open_exposure),
        "used_margin": float(used_margin),
        "peak_equity": float(peak_equity),
        "updated_at": updated_at,
        "currency": snapshot.currency,
    }


def _normalize_instrument(instrument: Any) -> Optional[Dict[str, Any]]:
    if instrument is None or not isinstance(instrument, InstrumentSpec):
        return None

    fields = {
        "contract_size": _coerce_float(instrument.contract_size, "contract_size"),
        "tick_size": _coerce_float(instrument.tick_size, "tick_size"),
        "tick_value_per_lot": _coerce_float(instrument.tick_value_per_lot, "tick_value_per_lot"),
        "volume_min": _coerce_float(instrument.volume_min, "volume_min"),
        "volume_max": _coerce_float(instrument.volume_max, "volume_max"),
        "volume_step": _coerce_float(instrument.volume_step, "volume_step"),
        "leverage": _coerce_float(instrument.leverage, "leverage"),
        "round_trip_cost_per_lot": _coerce_float(instrument.round_trip_cost_per_lot, "round_trip_cost_per_lot"),
        "spread": _coerce_float(instrument.spread, "spread"),
    }

    for value in fields.values():
        if value is None:
            return None

    if fields["contract_size"] <= 0:
        return None
    if fields["tick_size"] <= 0:
        return None
    if fields["tick_value_per_lot"] <= 0:
        return None
    if fields["volume_min"] <= 0:
        return None
    if fields["volume_max"] <= 0:
        return None
    if fields["volume_step"] <= 0:
        return None
    if fields["leverage"] <= 0:
        return None
    if fields["round_trip_cost_per_lot"] < 0:
        return None
    if fields["spread"] < 0:
        return None

    return {
        "symbol": instrument.symbol,
        "contract_size": float(fields["contract_size"]),
        "tick_size": float(fields["tick_size"]),
        "tick_value_per_lot": float(fields["tick_value_per_lot"]),
        "volume_min": float(fields["volume_min"]),
        "volume_max": float(fields["volume_max"]),
        "volume_step": float(fields["volume_step"]),
        "leverage": float(fields["leverage"]),
        "round_trip_cost_per_lot": float(fields["round_trip_cost_per_lot"]),
        "spread": float(fields["spread"]),
        "account_currency": instrument.account_currency,
    }


@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str
    contract_size: float
    tick_size: float
    tick_value_per_lot: float
    volume_min: float
    volume_max: float
    volume_step: float
    round_trip_cost_per_lot: float = 0.0
    spread: float = 0.0
    leverage: float = 1.0
    account_currency: str = "USD"


@dataclass(frozen=True)
class AccountSnapshot:
    balance: float
    equity: float
    daily_pnl: float
    open_exposure: float
    used_margin: float
    peak_equity: float
    updated_at: datetime
    currency: str = "USD"

    def validate(self, *, now: Optional[datetime] = None, stale_seconds: int = 60) -> Optional[str]:
        snapshot_norm = _normalize_snapshot(self)
        if snapshot_norm is None:
            return "snapshot contains invalid numeric content or invalid datetime"

        if isinstance(stale_seconds, bool) or not isinstance(stale_seconds, int) or stale_seconds <= 0:
            return "stale_seconds must be a positive integer"

        updated_at = snapshot_norm["updated_at"]
        if now is None:
            now = datetime.now(timezone.utc)
        if not isinstance(now, datetime):
            return "now must be a datetime"
        if now.tzinfo is None or now.utcoffset() is None:
            return "now must be timezone-aware"
        if updated_at.tzinfo is None or updated_at.utcoffset() is None:
            return "updated_at must be timezone-aware"

        if updated_at > now + timedelta(seconds=30):
            return "snapshot is in the future"
        age = (now - updated_at).total_seconds()
        if age > stale_seconds:
            return "snapshot is stale"
        return None


@dataclass
class RiskDecision:
    allowed: bool
    reason: str = ""
    volume: float = 0.0
    risk_per_trade: float = 0.0
    risk_reward: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RiskEngineV2:
    """
    Isolated risk validation layer with strict broker-margin validation.

    Financial separation:
    - mathematical risk validation: stop, RR, daily loss, drawdown, risk budget
    - broker margin validation: exact required margin from broker-specific provider
    - margin utilization cap: used_margin + required_margin versus equity cap

    The margin provider is injected at construction time and receives:
      - symbol
      - side
      - exact volume
      - entry price
      - instrument object

    There is no direct bypass via margin_required override.
    """

    def __init__(
        self,
        *,
        risk_pct: float = 0.01,
        max_daily_loss_pct: float = 0.03,
        max_drawdown_pct: float = 0.20,
        max_margin_utilization_pct: float = 0.75,
        stale_seconds: int = 60,
        margin_provider: Optional[Callable[[str, int, float, float, InstrumentSpec], float]] = None,
    ) -> None:
        self._validate_constructor(
            risk_pct=risk_pct,
            max_daily_loss_pct=max_daily_loss_pct,
            max_drawdown_pct=max_drawdown_pct,
            max_margin_utilization_pct=max_margin_utilization_pct,
            stale_seconds=stale_seconds,
        )
        self.risk_pct = float(risk_pct)
        self.max_daily_loss_pct = float(max_daily_loss_pct)
        self.max_drawdown_pct = float(max_drawdown_pct)
        self.max_margin_utilization_pct = float(max_margin_utilization_pct)
        self.stale_seconds = int(stale_seconds)
        self.margin_provider = margin_provider

    def _validate_constructor(
        self,
        *,
        risk_pct: float,
        max_daily_loss_pct: float,
        max_drawdown_pct: float,
        max_margin_utilization_pct: float,
        stale_seconds: int,
    ) -> None:
        for name, value in {
            "risk_pct": risk_pct,
            "max_daily_loss_pct": max_daily_loss_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "max_margin_utilization_pct": max_margin_utilization_pct,
        }.items():
            f_value = _coerce_float(value, name)
            if f_value is None:
                raise ValueError(f"{name} must be a finite numeric value")
            if f_value <= 0:
                raise ValueError(f"{name} must be > 0")
            if f_value >= 1.0:
                raise ValueError(f"{name} must be < 1.0")

        if isinstance(stale_seconds, bool) or not isinstance(stale_seconds, int) or stale_seconds <= 0:
            raise ValueError("stale_seconds must be a positive integer")

    def _validate_instrument(self, symbol: str, instrument: Optional[InstrumentSpec]) -> Optional[str]:
        if symbol is None or not isinstance(symbol, str) or symbol == "":
            return "symbol is required"
        if instrument is None:
            return "instrument is required"
        if not isinstance(instrument, InstrumentSpec):
            return "instrument must be an InstrumentSpec instance"
        if instrument.symbol != symbol:
            return "instrument symbol does not match requested symbol"

        if not isinstance(instrument.account_currency, str) or instrument.account_currency.strip() == "":
            return "instrument.account_currency must be a non-empty string"

        normalized = _normalize_instrument(instrument)
        if normalized is None:
            return "instrument contains invalid numeric content"
        if normalized["symbol"] != symbol:
            return "instrument symbol does not match requested symbol"
        return None

    def _round_down_volume(self, volume: float, instrument: InstrumentSpec) -> Optional[float]:
        step = _coerce_float(instrument.volume_step, "instrument.volume_step")
        if step is None or step <= 0:
            return None

        try:
            volume_dec = Decimal(str(volume))
            step_dec = Decimal(str(step))
        except (InvalidOperation, OverflowError, ValueError):
            return None

        try:
            rounded = (volume_dec / step_dec).to_integral_value(ROUND_DOWN) * step_dec
        except (InvalidOperation, OverflowError, ValueError):
            return None

        rounded_f = float(rounded)
        if not isfinite(rounded_f):
            return None
        return rounded_f

    def _directional_validation(self, side: int, entry: float, stop_loss: float, take_profit: float) -> Optional[str]:
        if isinstance(side, bool):
            return "side must be 1 or -1 (not bool)"
        if side == 1:
            if stop_loss >= entry:
                return "buy requires stop_loss < entry"
            if take_profit <= entry:
                return "buy requires take_profit > entry"
        elif side == -1:
            if stop_loss <= entry:
                return "sell requires stop_loss > entry"
            if take_profit >= entry:
                return "sell requires take_profit < entry"
        else:
            return "side must be 1 (buy) or -1 (sell)"
        return None

    def _risk_per_lot(self, instrument: InstrumentSpec, stop_distance: float) -> float:
        tick_count = stop_distance / max(instrument.tick_size, 1e-9)
        result = (tick_count * instrument.tick_value_per_lot) + instrument.round_trip_cost_per_lot
        if not isfinite(result):
            return float("nan")
        return max(result, 0.0)

    def _reward_per_lot(self, instrument: InstrumentSpec, reward_distance: float) -> float:
        tick_count = reward_distance / max(instrument.tick_size, 1e-9)
        result = (tick_count * instrument.tick_value_per_lot) - instrument.round_trip_cost_per_lot
        if not isfinite(result):
            return float("nan")
        return max(result, 0.0)

    def _resolve_margin_required(
        self,
        *,
        symbol: str,
        side: int,
        volume: float,
        entry: float,
        instrument: InstrumentSpec,
    ) -> Optional[float]:
        if self.margin_provider is None:
            return None

        try:
            required = self.margin_provider(symbol, side, volume, entry, instrument)
        except Exception:
            return None

        required_f = _coerce_float(required, "margin_provider result")
        if required_f is None or required_f <= 0 or not isfinite(required_f):
            return None

        return float(required_f)

    def evaluate_trade(
        self,
        *,
        symbol: str,
        side: int,
        entry: NumericLike,
        stop_loss: NumericLike,
        take_profit: NumericLike,
        instrument: Optional[InstrumentSpec],
        snapshot: Optional[AccountSnapshot],
        risk_pct: Optional[NumericLike] = None,
    ) -> RiskDecision:
        entry_f = _coerce_float(entry, "entry")
        sl_f = _coerce_float(stop_loss, "stop_loss")
        tp_f = _coerce_float(take_profit, "take_profit")

        if entry_f is None or sl_f is None or tp_f is None:
            return RiskDecision(False, "entry, stop_loss and take_profit must be numeric values")

        if isinstance(side, bool) or type(side) is not int:
            return RiskDecision(False, "side must be an int equal to 1 or -1")
        if side not in (1, -1):
            return RiskDecision(False, "side must be 1 (buy) or -1 (sell)")

        if entry_f <= 0 or sl_f <= 0 or tp_f <= 0:
            return RiskDecision(False, "entry, stop_loss and take_profit must be > 0")

        if not isinstance(symbol, str) or symbol.strip() == "":
            return RiskDecision(False, "symbol is required")

        if not isinstance(instrument, InstrumentSpec):
            return RiskDecision(False, "instrument must be an InstrumentSpec instance")

        if not isinstance(instrument.account_currency, str) or instrument.account_currency.strip() == "":
            return RiskDecision(False, "instrument.account_currency must be a non-empty string")

        instrument_error = self._validate_instrument(symbol, instrument)
        if instrument_error:
            return RiskDecision(False, instrument_error)

        if not isinstance(snapshot, AccountSnapshot):
            return RiskDecision(False, "snapshot must be an AccountSnapshot instance")
        if not isinstance(snapshot.currency, str) or snapshot.currency.strip() == "":
            return RiskDecision(False, "snapshot.currency must be a non-empty string")

        snapshot_error = snapshot.validate(stale_seconds=self.stale_seconds)
        if snapshot_error:
            return RiskDecision(False, snapshot_error)

        if snapshot.currency != instrument.account_currency:
            return RiskDecision(False, "instrument currency does not match account snapshot currency")

        directional_error = self._directional_validation(side, entry_f, sl_f, tp_f)
        if directional_error:
            return RiskDecision(False, directional_error)

        if snapshot.daily_pnl < -(snapshot.balance * self.max_daily_loss_pct):
            return RiskDecision(False, "daily loss limit reached")

        peak = max(snapshot.peak_equity, 1e-9)
        drawdown = (peak - snapshot.equity) / peak
        if not isfinite(drawdown):
            return RiskDecision(False, "drawdown is not finite")
        if drawdown > self.max_drawdown_pct:
            return RiskDecision(False, "drawdown limit reached")

        risk_fraction = _coerce_float(risk_pct if risk_pct is not None else self.risk_pct, "risk_pct")
        if risk_fraction is None or risk_fraction <= 0 or risk_fraction >= 1.0:
            return RiskDecision(False, "risk_pct must be finite, > 0 and < 1.0")

        if side == 1:
            stop_distance = abs(entry_f - sl_f)
            reward_distance = abs(tp_f - entry_f)
        else:
            stop_distance = abs(sl_f - entry_f)
            reward_distance = abs(entry_f - tp_f)

        if stop_distance <= 0 or reward_distance <= 0:
            return RiskDecision(False, "stop_distance and reward_distance must be > 0")

        normalized_instrument = InstrumentSpec(
            symbol=instrument.symbol,
            contract_size=float(_coerce_float(instrument.contract_size, "contract_size") or 0.0),
            tick_size=float(_coerce_float(instrument.tick_size, "tick_size") or 0.0),
            tick_value_per_lot=float(_coerce_float(instrument.tick_value_per_lot, "tick_value_per_lot") or 0.0),
            volume_min=float(_coerce_float(instrument.volume_min, "volume_min") or 0.0),
            volume_max=float(_coerce_float(instrument.volume_max, "volume_max") or 0.0),
            volume_step=float(_coerce_float(instrument.volume_step, "volume_step") or 0.0),
            round_trip_cost_per_lot=float(_coerce_float(instrument.round_trip_cost_per_lot, "round_trip_cost_per_lot") or 0.0),
            spread=float(_coerce_float(instrument.spread, "spread") or 0.0),
            leverage=float(_coerce_float(instrument.leverage, "leverage") or 0.0),
            account_currency=instrument.account_currency,
        )

        risk_per_lot = self._risk_per_lot(normalized_instrument, stop_distance)
        reward_per_lot = self._reward_per_lot(normalized_instrument, reward_distance)

        if not isfinite(risk_per_lot) or risk_per_lot <= 0:
            return RiskDecision(False, "computed risk per lot is invalid")
        if not isfinite(reward_per_lot) or reward_per_lot <= 0:
            return RiskDecision(False, "computed reward per lot is invalid")

        net_rr = reward_per_lot / max(risk_per_lot, 1e-9)
        if not isfinite(net_rr):
            return RiskDecision(False, "net RR is not finite")
        if net_rr < 2.0:
            return RiskDecision(False, "net RR after costs < 2.0", risk_reward=net_rr)

        max_risk_budget = snapshot.equity * risk_fraction
        if not isfinite(max_risk_budget):
            return RiskDecision(False, "risk budget is not finite")

        raw_volume = max_risk_budget / max(risk_per_lot, 1e-9)
        if not isfinite(raw_volume):
            return RiskDecision(False, "raw volume is not finite")

        volume = self._round_down_volume(raw_volume, normalized_instrument)
        if volume is None:
            return RiskDecision(False, "volume rounding failed; invalid step or numeric overflow", risk_per_trade=max_risk_budget, risk_reward=net_rr)

        if volume < normalized_instrument.volume_min:
            return RiskDecision(False, "requested volume is below broker minimum", volume=volume, risk_per_trade=max_risk_budget, risk_reward=net_rr)
        if volume > normalized_instrument.volume_max:
            return RiskDecision(False, "requested volume exceeds broker maximum", volume=volume, risk_per_trade=max_risk_budget, risk_reward=net_rr)

        actual_risk = volume * risk_per_lot
        if not isfinite(actual_risk):
            return RiskDecision(False, "actual risk is not finite")
        if actual_risk > max_risk_budget + 1e-9:
            return RiskDecision(False, "risk budget exceeded after volume rounding", volume=volume, risk_per_trade=actual_risk, risk_reward=net_rr)

        notional_exposure = volume * normalized_instrument.contract_size * abs(entry_f)
        if not isfinite(notional_exposure):
            return RiskDecision(False, "notional exposure is not finite")

        required_margin = self._resolve_margin_required(
            symbol=symbol,
            side=side,
            volume=volume,
            entry=entry_f,
            instrument=normalized_instrument,
        )
        if required_margin is None:
            return RiskDecision(
                False,
                "margin_required is required for a reliable validation; exact broker margin data is unavailable",
                volume=volume,
                risk_per_trade=actual_risk,
                risk_reward=net_rr,
                metadata={
                    "notional_exposure": notional_exposure,
                    "risk_at_stop": actual_risk,
                    "symbol": symbol,
                    "side": side,
                },
            )

        total_used_margin_after_trade = snapshot.used_margin + required_margin
        if not isfinite(total_used_margin_after_trade):
            return RiskDecision(False, "used margin after trade is not finite")

        if total_used_margin_after_trade > snapshot.equity * self.max_margin_utilization_pct:
            return RiskDecision(
                False,
                "margin utilization exceeds configured cap",
                volume=volume,
                risk_per_trade=actual_risk,
                risk_reward=net_rr,
                metadata={
                    "notional_exposure": notional_exposure,
                    "margin_required": required_margin,
                    "used_margin_before_trade": snapshot.used_margin,
                    "used_margin_after_trade": total_used_margin_after_trade,
                    "risk_at_stop": actual_risk,
                    "limit": snapshot.equity * self.max_margin_utilization_pct,
                },
            )

        return RiskDecision(
            True,
            "trade accepted",
            volume=volume,
            risk_per_trade=actual_risk,
            risk_reward=net_rr,
            metadata={
                "symbol": symbol,
                "side": side,
                "notional_exposure": notional_exposure,
                "used_margin_before_trade": snapshot.used_margin,
                "margin_required": required_margin,
                "used_margin_after_trade": total_used_margin_after_trade,
                "risk_at_stop": actual_risk,
                "risk_per_lot": risk_per_lot,
                "reward_per_lot": reward_per_lot,
                "stop_distance": stop_distance,
                "reward_distance": reward_distance,
                "open_exposure_before_trade": snapshot.open_exposure,
            },
        )
