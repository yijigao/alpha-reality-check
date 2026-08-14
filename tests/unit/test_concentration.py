import pandas as pd

from alpha_reality_check.concentration import (
    largest_symbol_profit_share,
    top_winner_contribution_ratio,
)


def test_top_winner_contribution() -> None:
    pnl = pd.Series([10.0, 5.0, 2.0, 1.0, 1.0, 1.0, -4.0])
    assert top_winner_contribution_ratio(pnl) == 19.0 / 20.0
    assert top_winner_contribution_ratio(pd.Series([-1.0, 0.0])) == 0.0


def test_largest_symbol_share_uses_positive_profit_only() -> None:
    frame = pd.DataFrame(
        {"symbol": ["A", "A", "B", "B"], "pnl": [4.0, -10.0, 3.0, 1.0]}
    )
    assert largest_symbol_profit_share(frame) == 0.5
    assert (
        largest_symbol_profit_share(pd.DataFrame({"symbol": ["A"], "pnl": [-1]})) == 0
    )
