from __future__ import annotations


def win_rate(results: list[float]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r > 0) / len(results)


def expectancy(results: list[float]) -> float:
    return sum(results) / len(results) if results else 0.0


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


__all__ = ["win_rate", "expectancy", "profit_factor", "average_win_loss"]
