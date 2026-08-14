# Alpha Reality Check

Evidence-first diagnostics for strategy decay, concentration risk, and backtest-to-live gaps.

**Not another backtester.** Alpha Reality Check audits trade-level results you
already have. It does not fetch market data, generate strategies, optimize
parameters, connect to an exchange, or execute trades.

The project is an early v0.1 MVP. Its deterministic reference policy is a
review aid—not a statistical truth and not evidence that a strategy will make
money.

## 30-second quick start

```bash
pip install alpha-reality-check
alpha-rc demo
```

## Input

UTF-8 CSV with two required columns:

```csv
exit_time,pnl,symbol,stage,regime
2025-01-01T12:00:00Z,1.25,ASSET_A,backtest,calm
2025-01-02T12:00:00Z,-0.40,ASSET_B,backtest,volatile
```

`pnl` is the net PnL of one closed trade. Optional columns are `symbol`,
`stage`, `fees`, `slippage`, `regime`, `side`, and `strategy_id`. Column names
can be mapped in YAML; see [input-schema.md](docs/input-schema.md).

Invalid timestamps, non-finite PnL, duplicate rows, and invalid configuration
fail explicitly. Missing optional dimensions produce warnings and only disable
the related analysis.

## Commands

```bash
alpha-rc audit trades.csv
alpha-rc audit trades.csv --config policy.yaml --json result.json --markdown report.md
alpha-rc compare --backtest backtest.csv --paper paper.csv --live live.csv
alpha-rc demo
alpha-rc validate-config policies/reference.yaml
alpha-rc schema
alpha-rc --version
```

Example terminal summary:

```text
Decision: CONTINUE | Decision scope: overall | Trades: 80 | Expectancy: 0.669388
```

Machine-readable JSON separates decision-scope `metrics` from
`overall_metrics`, `stage_metrics`, and `regime_metrics`. It also includes
stage comparisons, every evaluated gate, explicit warnings, and input metadata
without absolute local paths.

## Decisions

| Decision | Meaning |
|---|---|
| `CONTINUE` | The supplied sample satisfies every applicable continue gate in the reference policy. |
| `WATCH` | Evidence is insufficient or mixed; this is not automatically a negative result. |
| `PAUSE` | A decay or concentration warning crossed a pause threshold. |
| `REJECT` | The sample floor and multiple negative conditions were met. |

Decision priority is `REJECT > PAUSE > WATCH > CONTINUE`. Defaults are
documented in [reference-policy.md](docs/reference-policy.md) and can be
overridden with YAML. `--fail-on` supports `never`, `watch`, `pause`, and
`reject`; the default is `never`.

## Backtest / paper / live comparison

When `stage` is available, the audit computes metrics by stage and reports
target-minus-source gaps for expectancy, profit factor, win rate, and absolute
drawdown. The preferred comparisons are backtest → paper, paper → live, and
backtest → live. Missing stages remain `not_available`.

The top-level decision always uses the highest evidence stage present in the
fixed order `live > paper > backtest`. Its `decision_scope`, `metrics`, reason
codes, and gates are based only on that stage; lower stages never supplement
its sample count. Without a valid stage, the scope is `overall`. The `audit`
and `compare` commands share this behavior.

```bash
alpha-rc compare \
  --backtest results/backtest.csv \
  --paper results/paper.csv \
  --live results/live.csv
```

## What it measures

- expectancy, profit factor, win rate, cumulative PnL, and drawdown;
- deterministic bootstrap probability that mean trade PnL is positive;
- recent-versus-history expectancy decay;
- top-five winner and largest-symbol profit concentration;
- stage and regime breakdowns.

See [methodology.md](docs/methodology.md) for definitions.

## Limitations

The tool does not prove causality, statistical significance, execution
quality, or future profitability. An iid trade bootstrap may be inappropriate
for serially dependent strategies. PnL units and data completeness are the
user's responsibility. Read [limitations.md](docs/limitations.md) before using
a decision in a review process.

Nothing in this repository is investment advice.

## CI use

A minimal reusable shell step is documented in [ci-usage.md](docs/ci-usage.md).
The repository's own test matrix covers Python 3.11, 3.12, and 3.13 on Ubuntu.

## Contributing

Issues and focused pull requests are welcome. Start with
[CONTRIBUTING.md](CONTRIBUTING.md) and follow the code of conduct.

## Roadmap

The next candidates are documented in [ROADMAP.md](ROADMAP.md). They are plans,
not promises. v0.1 intentionally excludes Web UI, databases, cloud services,
market-data downloads, optimization, and trading.

## 中文简介

Alpha Reality Check 是一个“证据优先”的策略结果审计 CLI：读取你已有的交易
CSV，检查收益衰减、赢家集中度以及回测到模拟/实盘之间的落差。它不是回测器，
不连接交易所、不下单，也不承诺盈利。默认决策规则只是透明、可修改的参考政策。

## License

Apache-2.0.
