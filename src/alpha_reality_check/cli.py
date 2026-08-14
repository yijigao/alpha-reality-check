"""Command-line interface for Alpha Reality Check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
import typer
import yaml

from . import __version__
from .engine import audit_csv, audit_frame
from .input import load_csv
from .models import AuditError, FailOn
from .policy import load_policy, reference_policy_dict
from .reports import markdown_text, write_reports

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Evidence-first diagnostics for trade-level strategy results.",
)

FAIL_CODES = {"WATCH": 10, "PAUSE": 20, "REJECT": 30}
SEVERITY = {"CONTINUE": 0, "WATCH": 1, "PAUSE": 2, "REJECT": 3}
FAIL_THRESHOLD = {"never": 99, "watch": 1, "pause": 2, "reject": 3}


def _finish(result: dict[str, Any], fail_on: FailOn) -> None:
    typer.echo(
        f"Decision: {result['decision']} | "
        f"Decision scope: {result['decision_scope']} | "
        f"Trades: {result['metrics']['trade_count']} | "
        f"Expectancy: {result['metrics']['expectancy']:.6g}"
    )
    if SEVERITY[str(result["decision"])] >= FAIL_THRESHOLD[fail_on]:
        raise typer.Exit(code=FAIL_CODES.get(str(result["decision"]), 0))


def _error(exc: Exception) -> None:
    typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(code=2)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed version and exit."),
    ] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def audit(
    trades: Annotated[Path, typer.Argument(help="UTF-8 trade CSV.")],
    config: Annotated[Path | None, typer.Option("--config")] = None,
    json_output: Annotated[Path | None, typer.Option("--json")] = None,
    markdown: Annotated[Path | None, typer.Option("--markdown")] = None,
    fail_on: Annotated[FailOn, typer.Option("--fail-on")] = "never",
) -> None:
    """Audit one trade CSV."""
    try:
        policy = load_policy(config)
        result = audit_csv(trades, policy)
        write_reports(result, json_output, markdown)
        _finish(result, fail_on)
    except AuditError as exc:
        _error(exc)


@app.command()
def compare(
    backtest: Annotated[Path | None, typer.Option("--backtest")] = None,
    paper: Annotated[Path | None, typer.Option("--paper")] = None,
    live: Annotated[Path | None, typer.Option("--live")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    json_output: Annotated[Path | None, typer.Option("--json")] = None,
    markdown: Annotated[Path | None, typer.Option("--markdown")] = None,
    fail_on: Annotated[FailOn, typer.Option("--fail-on")] = "never",
) -> None:
    """Compare two or three explicitly labeled evidence stages."""
    try:
        supplied = {
            "backtest": backtest,
            "paper": paper,
            "live": live,
        }
        chosen = [(stage, path) for stage, path in supplied.items() if path is not None]
        if len(chosen) < 2:
            raise AuditError("COMPARE_REQUIRES_AT_LEAST_TWO_STAGE_FILES")
        policy = load_policy(config)
        frames: list[pd.DataFrame] = []
        warnings: list[str] = []
        sources: dict[str, str] = {}
        for stage, path in chosen:
            assert path is not None
            loaded = load_csv(path, policy)
            frame = loaded.frame.copy()
            if "stage" in frame.columns and bool(frame["stage"].notna().any()):
                warnings.append(f"STAGE_COLUMN_OVERRIDDEN_BY_COMPARE_FLAG: {stage}")
            frame["stage"] = stage
            frames.append(frame)
            warnings.extend(
                warning
                for warning in loaded.warnings
                if warning != "STAGE_ANALYSIS_NOT_AVAILABLE"
            )
            sources[stage] = path.name
        combined = pd.concat(frames, ignore_index=True).sort_values(
            "exit_time", kind="stable"
        )
        result = audit_frame(
            combined.reset_index(drop=True),
            policy,
            warnings=warnings,
            input_summary={
                "source_names": sources,
                "trade_count": int(len(combined)),
            },
        )
        write_reports(result, json_output, markdown)
        _finish(result, fail_on)
    except AuditError as exc:
        _error(exc)


@app.command()
def demo() -> None:
    """Run a deterministic synthetic example without network access."""
    rows = []
    for index in range(60):
        rows.append(
            {
                "exit_time": f"2025-01-{(index % 28) + 1:02d}T{index % 24:02d}:00:00Z",
                "pnl": 1.0 if index % 3 else -0.6,
                "symbol": f"ASSET_{chr(65 + index % 3)}",
            }
        )
    frame = pd.DataFrame(rows)
    frame["exit_time"] = pd.to_datetime(frame["exit_time"], utc=True)
    frame = frame.sort_values("exit_time", kind="stable").reset_index(drop=True)
    result = audit_frame(
        frame,
        load_policy(),
        warnings=["SYNTHETIC_DEMO_FIXED_PATTERN"],
        input_summary={"source_name": "synthetic_demo", "trade_count": len(frame)},
    )
    typer.echo(markdown_text(result))


@app.command("validate-config")
def validate_config(config: Path) -> None:
    """Validate a YAML policy without auditing data."""
    try:
        load_policy(config)
        typer.echo("VALID")
    except AuditError as exc:
        _error(exc)


@app.command()
def schema() -> None:
    """Print the v0.1 input and output schema summary."""
    payload = {
        "schema_version": "0.1.0",
        "input": {
            "format": "UTF-8 CSV",
            "required": {
                "exit_time": "ISO-compatible timestamp",
                "pnl": "finite number",
            },
            "optional": [
                "symbol",
                "stage",
                "fees",
                "slippage",
                "regime",
                "side",
                "strategy_id",
            ],
        },
        "decisions": ["CONTINUE", "WATCH", "PAUSE", "REJECT"],
        "decision_scope": {
            "without_stage": "overall",
            "stage_priority": ["live", "paper", "backtest"],
            "metrics": "metrics used by the top-level decision",
            "overall_metrics": "metrics for all input trades",
        },
        "output_required_keys": [
            "schema_version",
            "tool_version",
            "decision_scope",
            "decision",
            "reason_codes",
            "warnings",
            "metrics",
            "overall_metrics",
            "stage_metrics",
            "regime_metrics",
            "stage_comparison",
            "gate_results",
            "input_summary",
        ],
    }
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("reference-policy")
def reference_policy() -> None:
    """Print the default reference policy as YAML."""
    typer.echo(yaml.safe_dump(reference_policy_dict(), sort_keys=False))


if __name__ == "__main__":
    app()
