from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["fastlife"])


@router.get("/market")
def market_summary() -> dict[str, object]:
    return {
        "symbol": "XAUUSD",
        "mode": "analysis_only",
        "summary": "Market analysis stack initialized.",
    }


@router.get("/quant")
def quant_summary() -> dict[str, object]:
    return {
        "metrics": ["win_rate", "expectancy", "profit_factor", "max_drawdown"],
        "mode": "analysis_only",
    }


@router.get("/risk")
def risk_summary() -> dict[str, object]:
    return {
        "rules": ["RR minimum 1:2", "max 3 trades per day", "capital protection guard"],
        "mode": "analysis_only",
    }
