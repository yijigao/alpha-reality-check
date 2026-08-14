"""Transparent trade-level metric calculations."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .bootstrap import probability_expectancy_positive
from .concentration import largest_symbol_profit_share, top_winner_contribution_ratio
from .models import PolicyConfig


def _max_drawdown(pnl: pd.Series) -> float:
    cumulative = pnl.cumsum().to_numpy(dtype=float)
    equity = np.concatenate(([0.0], cumulative))
    peaks = np.maximum.accumulate(equity)
    return float(np.max(peaks - equity))


def _longest_losing_streak(pnl: pd.Series) -> int:
    longest = 0
    current = 0
    for value in pnl:
        if float(value) < 0.0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _profit_factor(gross_profit: float, gross_loss: float) -> tuple[float | None, str]:
    if gross_loss == 0.0 and gross_profit > 0.0:
        return None, "NO_LOSSES"
    if gross_profit == 0.0:
        return 0.0, "NO_PROFITS"
    return gross_profit / gross_loss, "FINITE"


def calculate_metrics(
    frame: pd.DataFrame,
    config: PolicyConfig,
    warnings: list[str],
    *,
    seed_offset: int = 0,
) -> dict[str, Any]:
    pnl = frame["pnl"].astype(float)
    count = int(len(pnl))
    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    profit_factor, profit_factor_state = _profit_factor(gross_profit, gross_loss)

    recent_window = min(
        count,
        max(config.recent_minimum_trades, math.ceil(config.recent_fraction * count)),
    )
    recent_expectancy = float(pnl.iloc[-recent_window:].mean())
    historical = pnl.iloc[:-recent_window]
    historical_expectancy: float | None = None
    decay: float | None = None
    if not historical.empty:
        historical_expectancy = float(historical.mean())
        if historical_expectancy != 0.0:
            decay = (recent_expectancy - historical_expectancy) / abs(
                historical_expectancy
            )
        else:
            warnings.append("RECENT_DECAY_NOT_AVAILABLE_ZERO_HISTORICAL_EXPECTANCY")
    else:
        warnings.append("RECENT_DECAY_NOT_AVAILABLE_NO_HISTORY_OUTSIDE_RECENT_WINDOW")

    bootstrap_probability: float | None = None
    if count >= config.bootstrap_minimum_trades:
        bootstrap_probability = probability_expectancy_positive(
            pnl.to_numpy(dtype=np.float64),
            resamples=config.bootstrap_resamples,
            seed=config.bootstrap_seed + seed_offset,
        )
    else:
        warnings.append(
            "BOOTSTRAP_NOT_REPORTED_INSUFFICIENT_SAMPLE: "
            f"{count}<{config.bootstrap_minimum_trades}"
        )

    symbol_share: float | None = None
    if "symbol" in frame.columns and bool(frame["symbol"].notna().any()):
        symbol_share = largest_symbol_profit_share(frame)

    return {
        "trade_count": count,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / count,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "profit_factor_state": profit_factor_state,
        "expectancy": float(pnl.mean()),
        "median_pnl": float(pnl.median()),
        "cumulative_pnl": float(pnl.sum()),
        "max_drawdown": _max_drawdown(pnl),
        "longest_losing_streak": _longest_losing_streak(pnl),
        "bootstrap_probability_expectancy_positive": bootstrap_probability,
        "bootstrap_resamples": (
            config.bootstrap_resamples if bootstrap_probability is not None else 0
        ),
        "recent_window_trades": recent_window,
        "recent_expectancy": recent_expectancy,
        "historical_expectancy": historical_expectancy,
        "recent_vs_history_decay": decay,
        "top_5_winner_contribution_ratio": top_winner_contribution_ratio(pnl),
        "largest_symbol_profit_share": symbol_share,
    }
