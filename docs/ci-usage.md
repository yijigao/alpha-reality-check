# CI usage

Install the repository and audit a committed or generated evidence CSV:

```yaml
- name: Audit strategy evidence
  run: |
    pip install .
    alpha-rc audit examples/healthy_strategy.csv \
      --json artifacts/decision.json \
      --markdown artifacts/report.md \
      --fail-on pause
```

`--fail-on never` is the default. Threshold modes return the decision's exit
code when its severity reaches the selected level: WATCH=10, PAUSE=20,
REJECT=30. Invalid input or configuration returns 2.

Persisting `artifacts/` is the caller's responsibility. The CLI never uploads
reports.
