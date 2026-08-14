"""Typed data models used by the audit pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Decision = Literal["CONTINUE", "WATCH", "PAUSE", "REJECT"]
FailOn = Literal["never", "watch", "pause", "reject"]


class AuditError(ValueError):
    """Raised when an input or configuration cannot be audited safely."""


@dataclass(frozen=True)
class ColumnMap:
    exit_time: str = "exit_time"
    pnl: str = "pnl"
    symbol: str = "symbol"
    stage: str = "stage"
    fees: str = "fees"
    slippage: str = "slippage"
    regime: str = "regime"
    side: str = "side"
    strategy_id: str = "strategy_id"

    def as_dict(self) -> dict[str, str]:
        return {
            "exit_time": self.exit_time,
            "pnl": self.pnl,
            "symbol": self.symbol,
            "stage": self.stage,
            "fees": self.fees,
            "slippage": self.slippage,
            "regime": self.regime,
            "side": self.side,
            "strategy_id": self.strategy_id,
        }


@dataclass(frozen=True)
class PolicyConfig:
    columns: ColumnMap
    bootstrap_resamples: int
    bootstrap_seed: int
    bootstrap_minimum_trades: int
    recent_minimum_trades: int
    recent_fraction: float
    minimum_watch_trades: int
    minimum_continue_trades: int
    continue_minimum_profit_factor: float
    continue_minimum_bootstrap_probability_positive: float
    continue_require_positive_expectancy: bool
    continue_require_non_negative_recent_expectancy: bool
    continue_maximum_top_5_winner_contribution_ratio: float
    continue_maximum_largest_symbol_profit_share: float
    pause_recent_expectancy_below: float
    pause_recent_decay_ratio_below: float
    pause_top_5_winner_contribution_ratio_above: float
    pause_largest_symbol_profit_share_above: float
    reject_minimum_trades: int
    reject_expectancy_at_or_below: float
    reject_profit_factor_below: float
    reject_bootstrap_probability_positive_below: float
    reject_minimum_negative_conditions: int


@dataclass
class LoadedTrades:
    frame: Any
    warnings: list[str]
    input_summary: dict[str, Any]


@dataclass(frozen=True)
class GateResult:
    code: str
    group: str
    triggered: bool
    available: bool
    actual: Any
    operator: str
    threshold: Any
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "group": self.group,
            "triggered": self.triggered,
            "available": self.available,
            "actual": self.actual,
            "operator": self.operator,
            "threshold": self.threshold,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class OutputPaths:
    json_path: Path | None = None
    markdown_path: Path | None = None
