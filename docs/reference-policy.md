# Reference policy

The default policy is a transparent review convention, not a statistical truth.
It can be printed with `alpha-rc reference-policy` and is committed as
`policies/reference.yaml`.

Decision priority is `REJECT > PAUSE > WATCH > CONTINUE`.

- `REJECT` requires its 50-trade floor and at least two of: non-positive
  expectancy, profit factor below 1.0, bootstrap probability below 0.30.
- `PAUSE` requires any configured recent-decay or concentration trigger.
- `WATCH` covers fewer than 20 trades or any sample that does not satisfy all
  applicable continue gates.
- `CONTINUE` requires at least 50 trades and every applicable continue gate.
  Bootstrap evidence is required by default; an unavailable bootstrap cannot
  qualify. Symbol concentration is skipped—not guessed—when symbol is absent.

Boolean expectancy gates explicitly configured to `false` are recorded as
disabled and never reported as triggered. Configuration validation rejects
non-finite thresholds, duplicate column mappings, a watch sample floor above
the continue floor, and a reject negative-condition count above the three
defined reject conditions.

For staged input, all thresholds are applied only to the highest evidence
stage present in the fixed order `live > paper > backtest`. Backtest and paper
rows never fill a live-stage sample requirement. Without a valid stage, the
policy applies to the overall sample.

Every evaluated condition is included in `gate_results` with its actual value,
operator, threshold, availability, and trigger state.
