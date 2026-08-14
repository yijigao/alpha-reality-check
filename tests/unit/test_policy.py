from pathlib import Path

import pytest

from alpha_reality_check.models import AuditError
from alpha_reality_check.policy import load_policy, parse_policy, reference_policy_dict


def test_defaults_and_partial_override(tmp_path: Path) -> None:
    policy = load_policy()
    assert policy.bootstrap_resamples == 2000
    config = tmp_path / "policy.yaml"
    config.write_text("bootstrap:\n  resamples: 25\n", encoding="utf-8")
    assert load_policy(config).bootstrap_resamples == 25
    assert reference_policy_dict()["sample"]["minimum_continue_trades"] == 50


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"unknown": 1}, "UNKNOWN_CONFIG_KEY"),
        ({"bootstrap": 5}, "MUST_BE_MAPPING"),
        ({"bootstrap": {"resamples": 0}}, "INVALID_INTEGER"),
        ({"bootstrap": {"seed": -1}}, "INVALID_INTEGER"),
        ({"recent": {"fraction": 0}}, "must be > 0"),
        ({"recent": {"fraction": 2}}, "INVALID_PROBABILITY"),
        ({"continue": {"require_positive_expectancy": 1}}, "INVALID_BOOLEAN"),
        ({"continue": {"minimum_profit_factor": "high"}}, "INVALID_NUMBER"),
        ({"columns": {"pnl": ""}}, "COLUMN_NAMES"),
        (
            {"columns": {"exit_time": "timestamp", "pnl": "timestamp"}},
            "COLUMN_MAPPING_VALUES_MUST_BE_UNIQUE",
        ),
        (
            {"continue": {"minimum_profit_factor": float("nan")}},
            "continue.minimum_profit_factor must be finite",
        ),
        (
            {"pause": {"recent_expectancy_below": float("inf")}},
            "pause.recent_expectancy_below must be finite",
        ),
        (
            {
                "sample": {
                    "minimum_watch_trades": 51,
                    "minimum_continue_trades": 50,
                }
            },
            "INVALID_SAMPLE_THRESHOLDS",
        ),
        (
            {"reject": {"minimum_negative_conditions": 4}},
            "INVALID_REJECT_THRESHOLD",
        ),
        ({"reject": {"minimum_negative_conditions": 1}}, "INVALID_INTEGER"),
    ],
)
def test_invalid_policy(payload: dict[str, object], match: str) -> None:
    with pytest.raises(AuditError, match=match):
        parse_policy(payload)


def test_invalid_yaml_root_and_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(AuditError, match="CONFIG_NOT_FOUND"):
        load_policy(missing)
    root = tmp_path / "root.yaml"
    root.write_text("- list\n", encoding="utf-8")
    with pytest.raises(AuditError, match="ROOT_MUST_BE_MAPPING"):
        load_policy(root)
    malformed = tmp_path / "bad.yaml"
    malformed.write_text("x: [\n", encoding="utf-8")
    with pytest.raises(AuditError, match="INVALID_YAML"):
        load_policy(malformed)
