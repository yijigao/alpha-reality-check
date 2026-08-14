import json

import pandas as pd

from alpha_reality_check.engine import audit_frame
from alpha_reality_check.policy import load_policy
from alpha_reality_check.reports import json_text, markdown_text
from alpha_reality_check.stages import compare_stages, grouped_metrics


def staged_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "exit_time": pd.date_range("2025-01-01", periods=40, tz="UTC"),
            "pnl": [1.0] * 20 + [-0.5] * 20,
            "stage": ["backtest"] * 20 + ["paper"] * 20,
            "regime": ["calm", "volatile"] * 20,
            "symbol": ["A", "B"] * 20,
        }
    )


def test_grouped_metrics_and_comparisons() -> None:
    warnings: list[str] = []
    stages = grouped_metrics(staged_frame(), "stage", load_policy(), warnings)
    comparisons = compare_stages(stages)
    assert comparisons["backtest_to_paper"]["expectancy_gap"] == -1.5
    assert comparisons["paper_to_live"] == "not_available"
    assert grouped_metrics(staged_frame(), "missing", load_policy(), []) == {}


def test_reports_are_parseable_and_conclusion_first() -> None:
    result = audit_frame(staged_frame(), load_policy())
    encoded = json_text(result)
    payload = json.loads(encoded)
    assert payload["schema_version"] == "0.1.0"
    assert payload["decision_scope"] == "paper"
    assert payload["metrics"] == payload["stage_metrics"]["paper"]
    assert payload["overall_metrics"]["trade_count"] == 40
    assert "stage_metrics" not in payload["metrics"]
    assert "regime_metrics" not in payload["metrics"]
    markdown = markdown_text(result)
    assert markdown.startswith(f"# Decision: {result['decision']}")
    assert "**Decision scope:** paper" in markdown
    assert "## Stage comparison" in markdown
    assert "not investment advice" in markdown


def _evidence_frame(stage_counts: list[tuple[str, int, float]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    timestamp = pd.Timestamp("2025-01-01", tz="UTC")
    for stage, count, pnl in stage_counts:
        for _ in range(count):
            rows.append(
                {
                    "exit_time": timestamp,
                    "pnl": pnl,
                    "stage": stage,
                    "symbol": "ASSET_A",
                }
            )
            timestamp += pd.Timedelta(minutes=1)
    return pd.DataFrame(rows)


def test_live_scope_does_not_borrow_backtest_sample() -> None:
    combined = _evidence_frame([("backtest", 80, 1.0), ("live", 10, -1.0)])
    result = audit_frame(combined, load_policy())
    assert result["decision_scope"] == "live"
    assert result["decision"] == "WATCH"
    assert result["metrics"]["trade_count"] == 10
    assert result["overall_metrics"]["trade_count"] == 90
    continue_sample = next(
        gate
        for gate in result["gate_results"]
        if gate["code"] == "SAMPLE_MEETS_CONTINUE_MINIMUM"
    )
    assert continue_sample["triggered"] is False
    live_only = combined.loc[combined["stage"] == "live"].reset_index(drop=True)
    assert audit_frame(live_only, load_policy())["metrics"] == result["metrics"]


def test_sustained_negative_live_scope_cannot_continue() -> None:
    result = audit_frame(
        _evidence_frame([("backtest", 80, 1.0), ("live", 30, -1.0)]),
        load_policy(),
    )
    assert result["decision_scope"] == "live"
    assert result["decision"] in {"PAUSE", "REJECT"}
    assert result["decision"] != "CONTINUE"


def test_no_stage_uses_overall_scope() -> None:
    frame = _evidence_frame([("backtest", 60, 1.0)]).drop(columns=["stage", "symbol"])
    result = audit_frame(frame, load_policy())
    assert result["decision_scope"] == "overall"
    assert result["metrics"] == result["overall_metrics"]
    assert result["decision"] == "CONTINUE"


def test_paper_is_highest_scope_without_live() -> None:
    result = audit_frame(
        _evidence_frame([("backtest", 80, 1.0), ("paper", 30, 0.5)]),
        load_policy(),
    )
    assert result["decision_scope"] == "paper"
    assert result["metrics"]["trade_count"] == 30
