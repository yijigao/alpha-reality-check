# Methodology

Alpha Reality Check consumes closed-trade net PnL records sorted by
`exit_time`. It does not reconstruct entries, fills, or market conditions.

## Core metrics

- `trade_count`: all valid rows, including zero-PnL trades.
- `wins` / `losses`: PnL strictly above / below zero.
- `win_rate`: wins divided by all trades.
- `gross_profit`: sum of positive PnL.
- `gross_loss`: absolute sum of negative PnL.
- `profit_factor`: gross profit divided by gross loss. When there are profits
  but no losses, JSON uses `null` with `profit_factor_state=NO_LOSSES`; it never
  emits a fake finite value. When there are no profits, profit factor is zero.
- `expectancy` / `median_pnl`: mean / median trade PnL.
- `cumulative_pnl`: sum of trade PnL.
- `max_drawdown`: largest absolute peak-to-trough fall in cumulative PnL,
  starting from zero and ordered by exit time.
- `longest_losing_streak`: longest consecutive run of negative trades.

## Bootstrap

The default is 2,000 iid resamples with replacement and seed 1729. The metric
is the fraction of resampled mean PnLs strictly above zero. It is not reported
below the configured 20-trade floor. Determinism supports review; it does not
remove model risk or establish statistical significance.

## Decay

The recent window is the last `max(20, ceil(30% × N))` trades, capped at N.
Historical expectancy uses the preceding trades. Decay is:

```text
(recent expectancy - historical expectancy) / abs(historical expectancy)
```

It is unavailable when no earlier trades exist or historical expectancy is
zero.

## Concentration

```text
top_5_winner_contribution_ratio = five largest positive PnLs / gross profit
largest_symbol_profit_share = largest symbol positive-PnL sum / gross profit
```

Losses are not netted against winners in these concentration denominators.

## Stage gaps

For backtest → paper, paper → live, and backtest → live, every gap is
`target - source`. A positive drawdown gap means the target stage had a larger
absolute drawdown. Missing stages or non-finite profit factors produce
`not_available`.
