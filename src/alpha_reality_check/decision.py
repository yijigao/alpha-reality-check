"""Deterministic reference decision engine."""

from __future__ import annotations

from typing import Any

from .models import Decision, GateResult, PolicyConfig


def _gate(
    code: str,
    group: str,
    actual: Any,
    operator: str,
    threshold: Any,
    triggered: bool,
    *,
    available: bool = True,
    detail: str = "",
) -> GateResult:
    return GateResult(
        code=code,
        group=group,
        triggered=triggered,
        available=available,
        actual=actual,
        operator=operator,
        threshold=threshold,
        detail=detail,
    )


def _effective_profit_factor(metrics: dict[str, Any]) -> float | None:
    value = metrics["profit_factor"]
    if value is not None:
        return float(value)
    if metrics["profit_factor_state"] == "NO_LOSSES":
        return float("inf")
    return None


def decide(
    metrics: dict[str, Any], config: PolicyConfig
) -> tuple[Decision, list[str], list[dict[str, Any]]]:
    gates: list[GateResult] = []
    count = int(metrics["trade_count"])
    pf = _effective_profit_factor(metrics)
    bootstrap = metrics["bootstrap_probability_expectancy_positive"]
    symbol_share = metrics["largest_symbol_profit_share"]
    decay = metrics["recent_vs_history_decay"]

    sample_watch = count < config.minimum_watch_trades
    sample_continue = count >= config.minimum_continue_trades
    gates.append(
        _gate(
            "SAMPLE_BELOW_WATCH_MINIMUM",
            "sample",
            count,
            "<",
            config.minimum_watch_trades,
            sample_watch,
            detail="Evidence is insufficient; this is not a negative finding.",
        )
    )
    gates.append(
        _gate(
            "SAMPLE_MEETS_CONTINUE_MINIMUM",
            "sample",
            count,
            ">=",
            config.minimum_continue_trades,
            sample_continue,
        )
    )

    reject_conditions = [
        _gate(
            "REJECT_EXPECTANCY_NON_POSITIVE",
            "reject",
            metrics["expectancy"],
            "<=",
            config.reject_expectancy_at_or_below,
            float(metrics["expectancy"]) <= config.reject_expectancy_at_or_below,
        ),
        _gate(
            "REJECT_PROFIT_FACTOR_BELOW",
            "reject",
            metrics["profit_factor"],
            "<",
            config.reject_profit_factor_below,
            pf is not None and pf < config.reject_profit_factor_below,
            available=pf is not None,
        ),
        _gate(
            "REJECT_BOOTSTRAP_PROBABILITY_BELOW",
            "reject",
            bootstrap,
            "<",
            config.reject_bootstrap_probability_positive_below,
            bootstrap is not None
            and float(bootstrap) < config.reject_bootstrap_probability_positive_below,
            available=bootstrap is not None,
        ),
    ]
    gates.extend(reject_conditions)
    negative_count = sum(gate.triggered for gate in reject_conditions)
    reject_sample_met = count >= config.reject_minimum_trades
    gates.append(
        _gate(
            "REJECT_MINIMUM_SAMPLE_MET",
            "reject",
            count,
            ">=",
            config.reject_minimum_trades,
            reject_sample_met,
        )
    )
    reject_triggered = (
        reject_sample_met
        and negative_count >= config.reject_minimum_negative_conditions
    )
    gates.append(
        _gate(
            "REJECT_MULTIPLE_NEGATIVE_CONDITIONS",
            "reject",
            negative_count,
            ">=",
            config.reject_minimum_negative_conditions,
            reject_triggered,
            detail=(
                "REJECT requires multiple negative conditions plus its sample floor."
            ),
        )
    )

    pause_conditions = [
        _gate(
            "PAUSE_RECENT_EXPECTANCY_NEGATIVE",
            "pause",
            metrics["recent_expectancy"],
            "<",
            config.pause_recent_expectancy_below,
            count >= config.minimum_watch_trades
            and float(metrics["recent_expectancy"])
            < config.pause_recent_expectancy_below,
            available=count >= config.minimum_watch_trades,
        ),
        _gate(
            "PAUSE_RECENT_DECAY_SEVERE",
            "pause",
            decay,
            "<",
            config.pause_recent_decay_ratio_below,
            count >= config.minimum_watch_trades
            and decay is not None
            and float(decay) < config.pause_recent_decay_ratio_below,
            available=count >= config.minimum_watch_trades and decay is not None,
        ),
        _gate(
            "PAUSE_TOP_WINNERS_CONCENTRATED",
            "pause",
            metrics["top_5_winner_contribution_ratio"],
            ">",
            config.pause_top_5_winner_contribution_ratio_above,
            count >= config.minimum_watch_trades
            and float(metrics["top_5_winner_contribution_ratio"])
            > config.pause_top_5_winner_contribution_ratio_above,
            available=count >= config.minimum_watch_trades,
        ),
        _gate(
            "PAUSE_SYMBOL_PROFIT_CONCENTRATED",
            "pause",
            symbol_share,
            ">",
            config.pause_largest_symbol_profit_share_above,
            count >= config.minimum_watch_trades
            and symbol_share is not None
            and float(symbol_share) > config.pause_largest_symbol_profit_share_above,
            available=count >= config.minimum_watch_trades and symbol_share is not None,
        ),
    ]
    gates.extend(pause_conditions)
    pause_triggered = any(gate.triggered for gate in pause_conditions)

    profit_factor_gate = _gate(
        "CONTINUE_PROFIT_FACTOR_MET",
        "continue",
        metrics["profit_factor"],
        ">=",
        config.continue_minimum_profit_factor,
        pf is not None and pf >= config.continue_minimum_profit_factor,
        available=pf is not None,
    )
    bootstrap_gate = _gate(
        "CONTINUE_BOOTSTRAP_PROBABILITY_MET",
        "continue",
        bootstrap,
        ">=",
        config.continue_minimum_bootstrap_probability_positive,
        bootstrap is not None
        and float(bootstrap) >= config.continue_minimum_bootstrap_probability_positive,
        available=bootstrap is not None,
        detail=("Required evidence is unavailable." if bootstrap is None else ""),
    )
    expectancy_gate = _gate(
        "CONTINUE_EXPECTANCY_POSITIVE",
        "continue",
        metrics["expectancy"],
        ">",
        0.0,
        config.continue_require_positive_expectancy
        and float(metrics["expectancy"]) > 0.0,
        available=config.continue_require_positive_expectancy,
        detail=(
            "Disabled by policy: continue.require_positive_expectancy=false."
            if not config.continue_require_positive_expectancy
            else ""
        ),
    )
    recent_expectancy_gate = _gate(
        "CONTINUE_RECENT_EXPECTANCY_NON_NEGATIVE",
        "continue",
        metrics["recent_expectancy"],
        ">=",
        0.0,
        config.continue_require_non_negative_recent_expectancy
        and float(metrics["recent_expectancy"]) >= 0.0,
        available=config.continue_require_non_negative_recent_expectancy,
        detail=(
            "Disabled by policy: continue.require_non_negative_recent_expectancy=false."
            if not config.continue_require_non_negative_recent_expectancy
            else ""
        ),
    )
    winner_concentration_gate = _gate(
        "CONTINUE_TOP_WINNER_CONCENTRATION_ACCEPTABLE",
        "continue",
        metrics["top_5_winner_contribution_ratio"],
        "<=",
        config.continue_maximum_top_5_winner_contribution_ratio,
        float(metrics["top_5_winner_contribution_ratio"])
        <= config.continue_maximum_top_5_winner_contribution_ratio,
    )
    symbol_concentration_gate = _gate(
        "CONTINUE_SYMBOL_CONCENTRATION_ACCEPTABLE",
        "continue",
        symbol_share,
        "<=",
        config.continue_maximum_largest_symbol_profit_share,
        symbol_share is not None
        and float(symbol_share) <= config.continue_maximum_largest_symbol_profit_share,
        available=symbol_share is not None,
        detail="Skipped when symbol is not provided.",
    )
    continue_conditions = [
        profit_factor_gate,
        bootstrap_gate,
        expectancy_gate,
        recent_expectancy_gate,
        winner_concentration_gate,
        symbol_concentration_gate,
    ]
    gates.extend(continue_conditions)
    required_continue = [
        profit_factor_gate,
        bootstrap_gate,
        winner_concentration_gate,
    ]
    if config.continue_require_positive_expectancy:
        required_continue.append(expectancy_gate)
    if config.continue_require_non_negative_recent_expectancy:
        required_continue.append(recent_expectancy_gate)
    if symbol_concentration_gate.available:
        required_continue.append(symbol_concentration_gate)
    continue_triggered = sample_continue and all(
        gate.triggered for gate in required_continue
    )

    if reject_triggered:
        decision: Decision = "REJECT"
        reasons = ["REJECT_MULTIPLE_NEGATIVE_CONDITIONS"]
        reasons.extend(gate.code for gate in reject_conditions if gate.triggered)
    elif pause_triggered:
        decision = "PAUSE"
        reasons = [gate.code for gate in pause_conditions if gate.triggered]
    elif sample_watch:
        decision = "WATCH"
        reasons = ["SAMPLE_BELOW_WATCH_MINIMUM"]
    elif continue_triggered:
        decision = "CONTINUE"
        reasons = ["REFERENCE_CONTINUE_POLICY_SATISFIED"]
    else:
        decision = "WATCH"
        reasons = ["REFERENCE_CONTINUE_POLICY_NOT_FULLY_SATISFIED"]

    return decision, reasons, [gate.as_dict() for gate in gates]
