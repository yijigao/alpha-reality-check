from pathlib import Path

import pandas as pd
import pytest

from alpha_reality_check.input import load_csv
from alpha_reality_check.models import AuditError
from alpha_reality_check.policy import load_policy, parse_policy


def write_csv(path: Path, rows: list[dict[str, object]]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def valid_rows() -> list[dict[str, object]]:
    return [
        {"exit_time": "2025-01-02T00:00:00Z", "pnl": -1, "symbol": "A"},
        {"exit_time": "2025-01-01T00:00:00Z", "pnl": 2, "symbol": "B"},
    ]


def test_load_sorts_and_warns_for_missing_dimensions(tmp_path: Path) -> None:
    loaded = load_csv(write_csv(tmp_path / "trades.csv", valid_rows()), load_policy())
    assert list(loaded.frame["pnl"]) == [2.0, -1.0]
    assert loaded.input_summary["source_name"] == "trades.csv"
    assert "STAGE_ANALYSIS_NOT_AVAILABLE" in loaded.warnings
    assert "/" not in loaded.input_summary["source_name"]


def test_custom_mapping(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "mapped.csv",
        [
            {"close_time": "2025-01-01", "net": 1},
            {"close_time": "2025-01-02", "net": -1},
        ],
    )
    config = parse_policy({"columns": {"exit_time": "close_time", "pnl": "net"}})
    assert len(load_csv(path, config).frame) == 2


@pytest.mark.parametrize(
    "rows,match",
    [
        ([{"exit_time": "2025-01-01", "pnl": 1}], "INSUFFICIENT_TRADES"),
        (
            [{"exit_time": "bad", "pnl": 1}, {"exit_time": "2025", "pnl": 2}],
            "INVALID_EXIT_TIME",
        ),
        (
            [{"exit_time": "2025", "pnl": "nan"}, {"exit_time": "2026", "pnl": 2}],
            "INVALID_PNL",
        ),
        (
            [{"exit_time": "2025", "pnl": "inf"}, {"exit_time": "2026", "pnl": 2}],
            "INVALID_PNL",
        ),
        (
            [{"exit_time": "2025", "pnl": 1}, {"exit_time": "2025", "pnl": 1}],
            "DUPLICATE_ROWS",
        ),
        (
            [
                {"exit_time": "2025", "pnl": 1, "stage": "foo"},
                {"exit_time": "2026", "pnl": 2, "stage": "live"},
            ],
            "INVALID_STAGE",
        ),
        (
            [
                {"exit_time": "2025", "pnl": 1, "fees": "x"},
                {"exit_time": "2026", "pnl": 2, "fees": 0},
            ],
            "INVALID_FEES",
        ),
    ],
)
def test_invalid_rows(
    tmp_path: Path, rows: list[dict[str, object]], match: str
) -> None:
    with pytest.raises(AuditError, match=match):
        load_csv(write_csv(tmp_path / "bad.csv", rows), load_policy())


def test_missing_required_and_file(tmp_path: Path) -> None:
    with pytest.raises(AuditError, match="INPUT_NOT_FOUND"):
        load_csv(tmp_path / "none.csv", load_policy())
    path = write_csv(tmp_path / "missing.csv", [{"pnl": 1}, {"pnl": 2}])
    with pytest.raises(AuditError, match="MISSING_REQUIRED"):
        load_csv(path, load_policy())


def test_optional_missing_values_warn(tmp_path: Path) -> None:
    rows = [
        {"exit_time": "2025-01-01", "pnl": 1, "symbol": ""},
        {"exit_time": "2025-01-02", "pnl": 2, "symbol": "A"},
    ]
    loaded = load_csv(write_csv(tmp_path / "partial.csv", rows), load_policy())
    assert loaded.frame["symbol"].isna().sum() == 1
    assert any("SYMBOL_MISSING_FOR_1" in item for item in loaded.warnings)
