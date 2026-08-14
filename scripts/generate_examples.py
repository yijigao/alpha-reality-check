"""Generate committed example CSVs from one fixed random seed."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260814
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples"
ASSETS = np.array(["ASSET_A", "ASSET_B", "ASSET_C"])


def _frame(pnl: np.ndarray, *, start: str, stage: str | None = None) -> pd.DataFrame:
    size = len(pnl)
    frame = pd.DataFrame(
        {
            "exit_time": pd.date_range(start, periods=size, freq="12h", tz="UTC"),
            "pnl": np.round(pnl, 6),
            "symbol": ASSETS[np.arange(size) % len(ASSETS)],
            "regime": np.where(np.arange(size) % 4 == 0, "volatile", "calm"),
            "side": np.where(np.arange(size) % 2 == 0, "long", "short"),
            "strategy_id": "SYNTHETIC_EXAMPLE",
        }
    )
    if stage is not None:
        frame["stage"] = stage
    return frame


def main() -> None:
    rng = np.random.default_rng(SEED)
    OUTPUT.mkdir(exist_ok=True)

    healthy = _frame(rng.normal(0.55, 0.85, 80), start="2025-01-01")
    healthy.to_csv(OUTPUT / "healthy_strategy.csv", index=False)

    decayed_values = np.concatenate(
        [rng.normal(0.65, 0.75, 50), rng.normal(-1.10, 0.70, 30)]
    )
    _frame(decayed_values, start="2025-02-01").to_csv(
        OUTPUT / "decayed_strategy.csv", index=False
    )

    concentrated_values = rng.normal(-0.05, 0.20, 60)
    concentrated_values[[5, 16, 27, 38, 49]] = [7.0, 7.5, 8.0, 8.5, 9.0]
    _frame(concentrated_values, start="2025-03-01").to_csv(
        OUTPUT / "concentrated_strategy.csv", index=False
    )

    _frame(rng.normal(0.40, 0.60, 10), start="2025-04-01").to_csv(
        OUTPUT / "insufficient_evidence.csv", index=False
    )

    stages = pd.concat(
        [
            _frame(rng.normal(0.70, 0.80, 60), start="2025-01-01", stage="backtest"),
            _frame(rng.normal(0.15, 0.85, 60), start="2025-03-01", stage="paper"),
            _frame(rng.normal(-0.45, 0.90, 60), start="2025-05-01", stage="live"),
        ],
        ignore_index=True,
    )
    stages.to_csv(OUTPUT / "backtest_paper_live.csv", index=False)


if __name__ == "__main__":
    main()
