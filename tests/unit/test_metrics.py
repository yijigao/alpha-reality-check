import pandas as pd

from alpha_reality_check.metrics import calculate_metrics
from alpha_reality_check.policy import load_policy


def frame(values: list[float], symbols: bool = True) -> pd.DataFrame:
    data: dict[str, object] = {
        "exit_time": pd.date_range("2025-01-01", periods=len(values), tz="UTC"),
        "pnl": values,
    }
    if symbols:
        data["symbol"] = ["A" if index % 2 else "B" for index in range(len(values))]
    return pd.DataFrame(data)


def test_core_metrics_drawdown_and_streak() -> None:
    warnings: list[str] = []
    metrics = calculate_metrics(frame([2.0, -1.0, -3.0, 4.0]), load_policy(), warnings)
    assert metrics["trade_count"] == 4
    assert metrics["wins"] == 2
    assert metrics["losses"] == 2
    assert metrics["win_rate"] == 0.5
    assert metrics["gross_profit"] == 6.0
    assert metrics["gross_loss"] == 4.0
    assert metrics["profit_factor"] == 1.5
    assert metrics["max_drawdown"] == 4.0
    assert metrics["longest_losing_streak"] == 2
    assert metrics["bootstrap_probability_expectancy_positive"] is None
    assert any("BOOTSTRAP_NOT_REPORTED" in item for item in warnings)


def test_profit_factor_edge_cases() -> None:
    no_losses = calculate_metrics(frame([1.0, 2.0]), load_policy(), [])
    assert no_losses["profit_factor"] is None
    assert no_losses["profit_factor_state"] == "NO_LOSSES"
    no_profits = calculate_metrics(frame([-1.0, -2.0]), load_policy(), [])
    assert no_profits["profit_factor"] == 0.0
    assert no_profits["profit_factor_state"] == "NO_PROFITS"


def test_recent_decay_and_symbol_unavailable() -> None:
    values = [1.0] * 20 + [0.25] * 20
    metrics = calculate_metrics(frame(values, symbols=False), load_policy(), [])
    assert metrics["historical_expectancy"] == 1.0
    assert metrics["recent_expectancy"] == 0.25
    assert metrics["recent_vs_history_decay"] == -0.75
    assert metrics["largest_symbol_profit_share"] is None
    assert metrics["bootstrap_probability_expectancy_positive"] == 1.0


def test_zero_history_expectancy_warns() -> None:
    values = [1.0, -1.0] * 10 + [0.1] * 20
    warnings: list[str] = []
    metrics = calculate_metrics(frame(values), load_policy(), warnings)
    assert metrics["historical_expectancy"] == 0.0
    assert metrics["recent_vs_history_decay"] is None
    assert any("ZERO_HISTORICAL" in item for item in warnings)
