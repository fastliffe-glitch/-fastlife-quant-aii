from __future__ import annotations

from fastlife_quant.quant import average_win_loss, expectancy, profit_factor, win_rate


def test_quant_metrics():
    results = [0.5, -0.2, 0.8, -0.1, 1.2]
    assert win_rate(results) == 0.6
    assert expectancy(results) == 0.44
    assert profit_factor(results) == (1.5 / 0.3)
    assert average_win_loss(results) == (0.8333333333333333, 0.15)
