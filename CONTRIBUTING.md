# Contributing

Thank you for helping make strategy evidence easier to inspect.

1. Open or choose an issue before a material change.
2. Keep changes focused on deterministic, local evidence auditing.
3. Add tests for behavior and failure modes.
4. Run `ruff check .`, `ruff format --check .`, `mypy`, and the full pytest
   coverage command before opening a pull request.
5. Do not submit proprietary strategies, private data, credentials, exchange
   integrations, performance claims, or generated testimonials.

Development setup:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy
pytest --cov=alpha_reality_check --cov-report=term-missing --cov-fail-under=85
```

By participating, you agree to follow `CODE_OF_CONDUCT.md`.
