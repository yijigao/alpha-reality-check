"""Profit concentration diagnostics."""

from __future__ import annotations

import pandas as pd


def top_winner_contribution_ratio(pnl: pd.Series, count: int = 5) -> float:
    positive = pnl[pnl > 0].sort_values(ascending=False)
    gross_profit = float(positive.sum())
    if gross_profit == 0.0:
        return 0.0
    return float(positive.head(count).sum()) / gross_profit


def largest_symbol_profit_share(frame: pd.DataFrame) -> float:
    positive = frame.loc[frame["pnl"] > 0, ["symbol", "pnl"]].dropna()
    gross_profit = float(positive["pnl"].sum())
    if gross_profit == 0.0:
        return 0.0
    by_symbol = positive.groupby("symbol", sort=True)["pnl"].sum()
    return float(by_symbol.max()) / gross_profit
