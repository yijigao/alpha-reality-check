# Input schema

Input must be a UTF-8 CSV with at least two rows.

| Logical field | Required | Meaning |
|---|---|---|
| `exit_time` | yes | Timestamp parseable to UTC |
| `pnl` | yes | Finite net PnL for one closed trade |
| `symbol` | no | Instrument or neutral asset label |
| `stage` | no | `backtest`, `paper`, or `live` |
| `fees` | no | Finite informational field; not subtracted again |
| `slippage` | no | Finite informational field; not subtracted again |
| `regime` | no | User-defined regime label |
| `side` | no | User-defined side label |
| `strategy_id` | no | Strategy label |

The tool fails on missing required columns, malformed timestamps, null/NaN or
infinite PnL, invalid stage values, duplicate rows, and invalid optional numeric
fields. It never silently drops an invalid trade.

Custom mapping:

```yaml
columns:
  exit_time: close_time
  pnl: net_pnl
  symbol: instrument
  stage: source
```

Column mapping values must be non-empty and unique. Unknown configuration keys
fail validation.
