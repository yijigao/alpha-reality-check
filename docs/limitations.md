# Limitations

- Input PnL semantics cannot be independently verified by this tool.
- Trade-level iid bootstrap ignores serial correlation and overlapping bets.
- No correction is made for strategy selection, parameter search, survivorship,
  look-ahead, or data-snooping bias.
- Absolute drawdown is expressed in the input PnL unit, not as a percentage of
  capital.
- Fees and slippage columns are validated but not subtracted because `pnl` is
  defined as net PnL.
- Missing dimensions limit the related analysis; warnings preserve that fact.
- Stage gaps can reveal deterioration but do not identify its cause.
- Reference thresholds are configurable heuristics, not universal gates.
- A `CONTINUE` decision does not establish future profitability or authorize
  deployment. A `REJECT` decision only describes the supplied evidence under
  the selected policy.

This software is not investment advice.
