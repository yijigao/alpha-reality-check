"""Reference policy loading and validation."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any, cast

import yaml

from .models import AuditError, ColumnMap, PolicyConfig

DEFAULT_POLICY: dict[str, Any] = {
    "columns": {
        "exit_time": "exit_time",
        "pnl": "pnl",
        "symbol": "symbol",
        "stage": "stage",
        "fees": "fees",
        "slippage": "slippage",
        "regime": "regime",
        "side": "side",
        "strategy_id": "strategy_id",
    },
    "bootstrap": {"resamples": 2000, "seed": 1729, "minimum_trades": 20},
    "recent": {"minimum_trades": 20, "fraction": 0.30},
    "sample": {"minimum_watch_trades": 20, "minimum_continue_trades": 50},
    "continue": {
        "minimum_profit_factor": 1.25,
        "minimum_bootstrap_probability_positive": 0.80,
        "require_positive_expectancy": True,
        "require_non_negative_recent_expectancy": True,
        "maximum_top_5_winner_contribution_ratio": 0.60,
        "maximum_largest_symbol_profit_share": 0.50,
    },
    "pause": {
        "recent_expectancy_below": 0.0,
        "recent_decay_ratio_below": -0.50,
        "top_5_winner_contribution_ratio_above": 0.75,
        "largest_symbol_profit_share_above": 0.70,
    },
    "reject": {
        "minimum_trades": 50,
        "expectancy_at_or_below": 0.0,
        "profit_factor_below": 1.0,
        "bootstrap_probability_positive_below": 0.30,
        "minimum_negative_conditions": 2,
    },
}


def _merge_strict(
    base: dict[str, Any], override: dict[str, Any], prefix: str = ""
) -> None:
    for key, value in override.items():
        location = f"{prefix}.{key}" if prefix else key
        if key not in base:
            raise AuditError(f"UNKNOWN_CONFIG_KEY: {location}")
        if isinstance(base[key], dict):
            if not isinstance(value, dict):
                raise AuditError(f"CONFIG_SECTION_MUST_BE_MAPPING: {location}")
            _merge_strict(base[key], cast(dict[str, Any], value), location)
        else:
            base[key] = value


def _integer(value: Any, location: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise AuditError(f"INVALID_INTEGER: {location} must be >= {minimum}")
    return value


def _number(value: Any, location: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AuditError(f"INVALID_NUMBER: {location}")
    number = float(value)
    if not math.isfinite(number):
        raise AuditError(f"INVALID_NUMBER: {location} must be finite")
    return number


def _probability(value: Any, location: str) -> float:
    number = _number(value, location)
    if not 0.0 <= number <= 1.0:
        raise AuditError(f"INVALID_PROBABILITY: {location}")
    return number


def _boolean(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise AuditError(f"INVALID_BOOLEAN: {location}")
    return value


def parse_policy(raw: dict[str, Any]) -> PolicyConfig:
    merged = copy.deepcopy(DEFAULT_POLICY)
    _merge_strict(merged, raw)
    columns_raw = cast(dict[str, Any], merged["columns"])
    if not all(
        isinstance(value, str) and value.strip() for value in columns_raw.values()
    ):
        raise AuditError("COLUMN_NAMES_MUST_BE_NON_EMPTY_STRINGS")
    if len(set(columns_raw.values())) != len(columns_raw):
        raise AuditError("COLUMN_MAPPING_VALUES_MUST_BE_UNIQUE")
    columns = ColumnMap(**cast(dict[str, str], columns_raw))

    bootstrap = cast(dict[str, Any], merged["bootstrap"])
    recent = cast(dict[str, Any], merged["recent"])
    sample = cast(dict[str, Any], merged["sample"])
    continue_policy = cast(dict[str, Any], merged["continue"])
    pause = cast(dict[str, Any], merged["pause"])
    reject = cast(dict[str, Any], merged["reject"])
    recent_fraction = _probability(recent["fraction"], "recent.fraction")
    if recent_fraction == 0.0:
        raise AuditError("INVALID_PROBABILITY: recent.fraction must be > 0")

    policy = PolicyConfig(
        columns=columns,
        bootstrap_resamples=_integer(bootstrap["resamples"], "bootstrap.resamples"),
        bootstrap_seed=_integer(bootstrap["seed"], "bootstrap.seed", minimum=0),
        bootstrap_minimum_trades=_integer(
            bootstrap["minimum_trades"], "bootstrap.minimum_trades", minimum=2
        ),
        recent_minimum_trades=_integer(
            recent["minimum_trades"], "recent.minimum_trades", minimum=2
        ),
        recent_fraction=recent_fraction,
        minimum_watch_trades=_integer(
            sample["minimum_watch_trades"], "sample.minimum_watch_trades", minimum=2
        ),
        minimum_continue_trades=_integer(
            sample["minimum_continue_trades"],
            "sample.minimum_continue_trades",
            minimum=2,
        ),
        continue_minimum_profit_factor=_number(
            continue_policy["minimum_profit_factor"],
            "continue.minimum_profit_factor",
        ),
        continue_minimum_bootstrap_probability_positive=_probability(
            continue_policy["minimum_bootstrap_probability_positive"],
            "continue.minimum_bootstrap_probability_positive",
        ),
        continue_require_positive_expectancy=_boolean(
            continue_policy["require_positive_expectancy"],
            "continue.require_positive_expectancy",
        ),
        continue_require_non_negative_recent_expectancy=_boolean(
            continue_policy["require_non_negative_recent_expectancy"],
            "continue.require_non_negative_recent_expectancy",
        ),
        continue_maximum_top_5_winner_contribution_ratio=_probability(
            continue_policy["maximum_top_5_winner_contribution_ratio"],
            "continue.maximum_top_5_winner_contribution_ratio",
        ),
        continue_maximum_largest_symbol_profit_share=_probability(
            continue_policy["maximum_largest_symbol_profit_share"],
            "continue.maximum_largest_symbol_profit_share",
        ),
        pause_recent_expectancy_below=_number(
            pause["recent_expectancy_below"], "pause.recent_expectancy_below"
        ),
        pause_recent_decay_ratio_below=_number(
            pause["recent_decay_ratio_below"], "pause.recent_decay_ratio_below"
        ),
        pause_top_5_winner_contribution_ratio_above=_probability(
            pause["top_5_winner_contribution_ratio_above"],
            "pause.top_5_winner_contribution_ratio_above",
        ),
        pause_largest_symbol_profit_share_above=_probability(
            pause["largest_symbol_profit_share_above"],
            "pause.largest_symbol_profit_share_above",
        ),
        reject_minimum_trades=_integer(
            reject["minimum_trades"], "reject.minimum_trades", minimum=2
        ),
        reject_expectancy_at_or_below=_number(
            reject["expectancy_at_or_below"], "reject.expectancy_at_or_below"
        ),
        reject_profit_factor_below=_number(
            reject["profit_factor_below"], "reject.profit_factor_below"
        ),
        reject_bootstrap_probability_positive_below=_probability(
            reject["bootstrap_probability_positive_below"],
            "reject.bootstrap_probability_positive_below",
        ),
        reject_minimum_negative_conditions=_integer(
            reject["minimum_negative_conditions"],
            "reject.minimum_negative_conditions",
            minimum=2,
        ),
    )
    if policy.minimum_watch_trades > policy.minimum_continue_trades:
        raise AuditError(
            "INVALID_SAMPLE_THRESHOLDS: sample.minimum_watch_trades must be <= "
            "sample.minimum_continue_trades"
        )
    if policy.reject_minimum_negative_conditions > 3:
        raise AuditError(
            "INVALID_REJECT_THRESHOLD: reject.minimum_negative_conditions must be <= 3"
        )
    return policy


def load_policy(path: Path | None = None) -> PolicyConfig:
    if path is None:
        return parse_policy({})
    if not path.is_file():
        raise AuditError(f"CONFIG_NOT_FOUND: {path.name}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise AuditError(f"INVALID_YAML: {exc}") from exc
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise AuditError("CONFIG_ROOT_MUST_BE_MAPPING")
    return parse_policy(cast(dict[str, Any], payload))


def reference_policy_dict() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_POLICY)
