from typing import Any

from alpha_reality_check.decision import decide
from alpha_reality_check.policy import load_policy


def metrics(**updates: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "trade_count": 60,
        "profit_factor": 2.0,
        "profit_factor_state": "FINITE",
        "expectancy": 1.0,
        "bootstrap_probability_expectancy_positive": 0.95,
        "recent_expectancy": 0.8,
        "recent_vs_history_decay": -0.2,
        "top_5_winner_contribution_ratio": 0.3,
        "largest_symbol_profit_share": 0.3,
    }
    base.update(updates)
    return base


def test_continue_and_no_loss_profit_factor() -> None:
    decision, reasons, gates = decide(metrics(), load_policy())
    assert decision == "CONTINUE"
    assert reasons == ["REFERENCE_CONTINUE_POLICY_SATISFIED"]
    assert len(gates) >= 10
    decision, _, _ = decide(
        metrics(profit_factor=None, profit_factor_state="NO_LOSSES"), load_policy()
    )
    assert decision == "CONTINUE"


def test_reject_requires_multiple_negatives() -> None:
    decision, reasons, _ = decide(
        metrics(expectancy=-1.0, profit_factor=0.5, recent_expectancy=0.1),
        load_policy(),
    )
    assert decision == "REJECT"
    assert "REJECT_MULTIPLE_NEGATIVE_CONDITIONS" in reasons
    decision, _, _ = decide(metrics(profit_factor=0.5), load_policy())
    assert decision == "WATCH"


def test_pause_and_insufficient_watch() -> None:
    decision, reasons, _ = decide(metrics(recent_expectancy=-0.1), load_policy())
    assert decision == "PAUSE"
    assert "PAUSE_RECENT_EXPECTANCY_NEGATIVE" in reasons
    decision, reasons, _ = decide(
        metrics(
            trade_count=10,
            recent_expectancy=-2.0,
            top_5_winner_contribution_ratio=1.0,
            bootstrap_probability_expectancy_positive=None,
        ),
        load_policy(),
    )
    assert decision == "WATCH"
    assert reasons == ["SAMPLE_BELOW_WATCH_MINIMUM"]


def test_missing_symbol_gate_is_skipped() -> None:
    decision, _, gates = decide(
        metrics(largest_symbol_profit_share=None), load_policy()
    )
    assert decision == "CONTINUE"
    symbol_gate = next(
        gate
        for gate in gates
        if gate["code"] == "CONTINUE_SYMBOL_CONCENTRATION_ACCEPTABLE"
    )
    assert symbol_gate["available"] is False
