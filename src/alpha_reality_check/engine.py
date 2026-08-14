"""End-to-end audit orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from . import __version__
from .decision import decide
from .input import load_csv
from .metrics import calculate_metrics
from .models import PolicyConfig
from .stages import compare_stages, grouped_metrics

STAGE_DECISION_PRIORITY = ("live", "paper", "backtest")


def _decision_scope(stage_metrics: dict[str, dict[str, Any]]) -> str:
    return next(
        (stage for stage in STAGE_DECISION_PRIORITY if stage in stage_metrics),
        "overall",
    )


def audit_frame(
    frame: pd.DataFrame,
    config: PolicyConfig,
    *,
    warnings: list[str] | None = None,
    input_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    all_warnings = list(warnings or [])
    overall_metrics = calculate_metrics(frame, config, all_warnings)
    stage_metrics = grouped_metrics(frame, "stage", config, all_warnings)
    regime_metrics = grouped_metrics(frame, "regime", config, all_warnings)
    decision_scope = _decision_scope(stage_metrics)
    metrics = (
        overall_metrics
        if decision_scope == "overall"
        else stage_metrics[decision_scope]
    )
    stage_comparison = compare_stages(stage_metrics)
    decision, reason_codes, gate_results = decide(metrics, config)
    return {
        "schema_version": "0.1.0",
        "tool_version": __version__,
        "decision_scope": decision_scope,
        "decision": decision,
        "reason_codes": reason_codes,
        "warnings": list(dict.fromkeys(all_warnings)),
        "metrics": metrics,
        "overall_metrics": overall_metrics,
        "stage_metrics": stage_metrics,
        "regime_metrics": regime_metrics,
        "stage_comparison": stage_comparison,
        "gate_results": gate_results,
        "input_summary": input_summary or {"trade_count": int(len(frame))},
    }


def audit_csv(path: Path, config: PolicyConfig) -> dict[str, Any]:
    loaded = load_csv(path, config)
    return audit_frame(
        loaded.frame,
        config,
        warnings=loaded.warnings,
        input_summary=loaded.input_summary,
    )
