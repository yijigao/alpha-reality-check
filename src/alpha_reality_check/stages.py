"""Stage and regime diagnostics."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .metrics import calculate_metrics
from .models import PolicyConfig

STAGE_PAIRS = (
    ("backtest", "paper"),
    ("paper", "live"),
    ("backtest", "live"),
)


def grouped_metrics(
    frame: pd.DataFrame,
    column: str,
    config: PolicyConfig,
    warnings: list[str],
) -> dict[str, dict[str, Any]]:
    if column not in frame.columns:
        return {}
    output: dict[str, dict[str, Any]] = {}
    values = sorted(str(value) for value in frame[column].dropna().unique())
    for index, value in enumerate(values, start=1):
        subset = frame.loc[frame[column] == value].reset_index(drop=True)
        local_warnings: list[str] = []
        output[value] = calculate_metrics(
            subset, config, local_warnings, seed_offset=index * 1009
        )
        if local_warnings:
            warnings.extend(
                f"{column.upper()}={value}: {item}" for item in local_warnings
            )
    return output


def _gap(source: dict[str, Any], target: dict[str, Any], metric: str) -> float | str:
    before = source.get(metric)
    after = target.get(metric)
    if before is None or after is None:
        return "not_available"
    return float(after) - float(before)


def compare_stages(stage_metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    for source_name, target_name in STAGE_PAIRS:
        key = f"{source_name}_to_{target_name}"
        if source_name not in stage_metrics or target_name not in stage_metrics:
            comparisons[key] = "not_available"
            continue
        source = stage_metrics[source_name]
        target = stage_metrics[target_name]
        comparisons[key] = {
            "expectancy_gap": _gap(source, target, "expectancy"),
            "profit_factor_gap": _gap(source, target, "profit_factor"),
            "win_rate_gap": _gap(source, target, "win_rate"),
            "drawdown_gap": _gap(source, target, "max_drawdown"),
        }
    return comparisons
