from __future__ import annotations


def win_rate(results: list[float]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r > 0) / len(results)


def expectancy(results: list[float]) -> float:
    if not results:
        return 0.0
    return sum(results) / len(results)


def profit_factor(results: list[float]) -> float:
    gains = sum(r for r in results if r > 0)
    losses = abs(sum(r for r in results if r < 0))
    return gains / losses if losses else float("inf") if gains else 0.0


def average_win_loss(results: list[float]) -> tuple[float, float]:
    wins = [r for r in results if r > 0]
    losses = [r for r in results if r < 0]
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    return avg_win, avg_loss


def max_drawdown(results: list[float]) -> float:
    balance = 0.0
    peak = 0.0
    worst = 0.0
    for value in results:
        balance += value
        if balance > peak:
            peak = balance
        worst = max(worst, peak - balance)
    return worst


def distribution_r(results: list[float]) -> dict[str, float]:
    if not results:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    import math
    mean = sum(results) / len(results)
    variance = sum((x - mean) ** 2 for x in results) / len(results)
    std = math.sqrt(variance)
    return {"mean": mean, "std": std, "min": min(results), "max": max(results)}


__all__ = [
    "win_rate",
    "expectancy",
    "profit_factor",
    "average_win_loss",
    "max_drawdown",
    "distribution_r",
]
