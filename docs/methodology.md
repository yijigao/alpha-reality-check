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

Resampling is batched so the temporary index matrix targets at most 1,000,000
cells (except when one unavoidable resample already exceeds that count). The
batch size changes memory use, not the configured number of resamples.

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

When at least one valid stage is present, the top-level decision scope is the
highest evidence stage in the fixed order `live > paper > backtest`. Decision
metrics, reasons, and gates use only that stage. Lower stages cannot supplement
its sample size. Without a valid stage the scope is `overall`. `overall_metrics`
always describes all rows, while `stage_metrics` and `regime_metrics` remain
separate diagnostic mappings.

For backtest → paper, paper → live, and backtest → live, every gap is
`target - source`. A positive drawdown gap means the target stage had a larger
absolute drawdown. Missing stages or non-finite profit factors produce
`not_available`.
