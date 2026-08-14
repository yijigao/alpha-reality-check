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
    assert json.loads(encoded)["schema_version"] == "0.1.0"
    markdown = markdown_text(result)
    assert markdown.startswith(f"# Decision: {result['decision']}")
    assert "## Stage comparison" in markdown
    assert "not investment advice" in markdown
