"""Stable JSON and conclusion-first Markdown reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def json_text(result: dict[str, Any]) -> str:
    return (
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )


def _display(value: Any) -> str:
    if value is None:
        return "not_available"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def markdown_text(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    summary = result["input_summary"]
    lines = [
        f"# Decision: {result['decision']}",
        "",
        f"**Decision scope:** {result['decision_scope']}",
        "",
        f"**Evidence reviewed:** {metrics['trade_count']} trades.",
        "",
        "## Why",
        "",
    ]
    reasons = result["reason_codes"] or ["No decision reason was recorded."]
    lines.extend(f"- `{reason}`" for reason in reasons)
    lines.extend(
        [
            "",
            "## Key metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
    )
    for key in (
        "trade_count",
        "win_rate",
        "profit_factor",
        "expectancy",
        "cumulative_pnl",
        "max_drawdown",
        "bootstrap_probability_expectancy_positive",
        "recent_expectancy",
        "historical_expectancy",
        "recent_vs_history_decay",
        "top_5_winner_contribution_ratio",
        "largest_symbol_profit_share",
    ):
        lines.append(f"| `{key}` | {_display(metrics.get(key))} |")

    lines.extend(["", "## Stage comparison", ""])
    comparisons = result["stage_comparison"]
    if not comparisons or all(
        value == "not_available" for value in comparisons.values()
    ):
        lines.append("Stage comparison is not available for this input.")
    else:
        for name, values in comparisons.items():
            lines.append(f"### {name}")
            lines.append("")
            if values == "not_available":
                lines.append("not_available")
            else:
                for metric, value in values.items():
                    lines.append(f"- `{metric}`: {_display(value)}")
            lines.append("")

    lines.extend(["## Warnings and limitations", ""])
    warnings = result["warnings"]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- No input-specific warnings were emitted.")
    lines.extend(
        [
            "- Decisions apply a configurable reference policy; they are not "
            "statistical truth.",
            "- Trade bootstrap assumes exchangeable observations; it does not "
            "prove future performance.",
            "- Results depend on the completeness and meaning of the supplied "
            "net PnL records.",
            "- This report is not investment advice.",
            "",
            "## Input summary",
            "",
        ]
    )
    for key, value in summary.items():
        lines.append(f"- `{key}`: {_display(value)}")
    return "\n".join(lines) + "\n"


def write_reports(
    result: dict[str, Any], json_path: Path | None, markdown_path: Path | None
) -> None:
    for path, content in (
        (json_path, json_text(result)),
        (markdown_path, markdown_text(result)),
    ):
        if path is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
