import json
from pathlib import Path

from typer.testing import CliRunner

from alpha_reality_check.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"


def test_version_schema_and_demo() -> None:
    version = runner.invoke(app, ["--version"])
    assert version.exit_code == 0
    assert version.stdout.strip() == "0.1.0"
    schema = runner.invoke(app, ["schema"])
    assert schema.exit_code == 0
    schema_payload = json.loads(schema.stdout)
    assert schema_payload["schema_version"] == "0.1.0"
    assert "decision_scope" in schema_payload["output_required_keys"]
    assert "overall_metrics" in schema_payload["output_required_keys"]
    assert "stage_metrics" in schema_payload["output_required_keys"]
    assert "regime_metrics" in schema_payload["output_required_keys"]
    assert schema_payload["decision_scope"]["stage_priority"] == [
        "live",
        "paper",
        "backtest",
    ]
    demo = runner.invoke(app, ["demo"])
    assert demo.exit_code == 0
    assert "# Decision: CONTINUE" in demo.stdout


def test_example_decisions_and_outputs(tmp_path: Path) -> None:
    expected = {
        "healthy_strategy.csv": "CONTINUE",
        "decayed_strategy.csv": "REJECT",
        "concentrated_strategy.csv": "PAUSE",
        "insufficient_evidence.csv": "WATCH",
    }
    for filename, decision in expected.items():
        output = tmp_path / f"{filename}.json"
        report = tmp_path / f"{filename}.md"
        result = runner.invoke(
            app,
            [
                "audit",
                str(EXAMPLES / filename),
                "--json",
                str(output),
                "--markdown",
                str(report),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert json.loads(output.read_text())["decision"] == decision
        assert report.read_text().startswith(f"# Decision: {decision}")


def test_fail_on_exit_codes() -> None:
    watch = runner.invoke(
        app,
        [
            "audit",
            str(EXAMPLES / "insufficient_evidence.csv"),
            "--fail-on",
            "watch",
        ],
    )
    assert watch.exit_code == 10
    pause = runner.invoke(
        app,
        [
            "audit",
            str(EXAMPLES / "concentrated_strategy.csv"),
            "--fail-on",
            "pause",
        ],
    )
    assert pause.exit_code == 20
    reject = runner.invoke(
        app,
        [
            "audit",
            str(EXAMPLES / "decayed_strategy.csv"),
            "--fail-on",
            "reject",
        ],
    )
    assert reject.exit_code == 30


def test_compare_and_validate_config(tmp_path: Path) -> None:
    output = tmp_path / "compare.json"
    result = runner.invoke(
        app,
        [
            "compare",
            "--backtest",
            str(EXAMPLES / "healthy_strategy.csv"),
            "--paper",
            str(EXAMPLES / "decayed_strategy.csv"),
            "--live",
            str(EXAMPLES / "concentrated_strategy.csv"),
            "--json",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.stdout
    comparison = json.loads(output.read_text())["stage_comparison"]
    assert comparison["backtest_to_paper"] != "not_available"
    compare_payload = json.loads(output.read_text())
    assert compare_payload["decision_scope"] == "live"
    assert compare_payload["metrics"] == compare_payload["stage_metrics"]["live"]
    valid = runner.invoke(
        app, ["validate-config", str(ROOT / "policies/reference.yaml")]
    )
    assert valid.exit_code == 0
    assert valid.stdout.strip() == "VALID"
    invalid = tmp_path / "bad.yaml"
    invalid.write_text("unknown: true\n")
    failed = runner.invoke(app, ["validate-config", str(invalid)])
    assert failed.exit_code == 2

    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text(
        "columns:\n  exit_time: timestamp\n  pnl: timestamp\n",
        encoding="utf-8",
    )
    duplicate_result = runner.invoke(app, ["validate-config", str(duplicate)])
    assert duplicate_result.exit_code == 2
    assert "COLUMN_MAPPING_VALUES_MUST_BE_UNIQUE" in duplicate_result.stderr

    non_finite = tmp_path / "non-finite.yaml"
    non_finite.write_text("pause:\n  recent_expectancy_below: .inf\n", encoding="utf-8")
    non_finite_result = runner.invoke(app, ["validate-config", str(non_finite)])
    assert non_finite_result.exit_code == 2
    assert "pause.recent_expectancy_below" in non_finite_result.stderr


def test_combined_stage_example_shows_decline(tmp_path: Path) -> None:
    output = tmp_path / "stages.json"
    result = runner.invoke(
        app,
        [
            "audit",
            str(EXAMPLES / "backtest_paper_live.csv"),
            "--json",
            str(output),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(output.read_text())
    stages = payload["stage_metrics"]
    assert stages["backtest"]["expectancy"] > stages["paper"]["expectancy"]
    assert stages["paper"]["expectancy"] > stages["live"]["expectancy"]
    assert payload["stage_comparison"]["backtest_to_live"]["expectancy_gap"] < 0
    assert payload["decision_scope"] == "live"
    assert payload["metrics"] == stages["live"]
    assert "Decision scope: live" in result.stdout


def test_invalid_cli_inputs() -> None:
    missing = runner.invoke(app, ["audit", "missing.csv"])
    assert missing.exit_code == 2
    compare = runner.invoke(
        app,
        ["compare", "--backtest", str(EXAMPLES / "healthy_strategy.csv")],
    )
    assert compare.exit_code == 2


def test_reference_policy_command() -> None:
    result = runner.invoke(app, ["reference-policy"])
    assert result.exit_code == 0
    assert "minimum_continue_trades: 50" in result.stdout
