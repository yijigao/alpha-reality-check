"""Deterministic bootstrap helpers."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

MAX_BOOTSTRAP_INDEX_CELLS = 1_000_000


def bootstrap_chunk_size(trade_count: int, resamples: int) -> int:
    """Return a bounded resample batch size for an index matrix."""
    if trade_count < 1:
        raise ValueError("trade_count must be positive")
    if resamples < 1:
        raise ValueError("resamples must be positive")
    return max(1, min(resamples, MAX_BOOTSTRAP_INDEX_CELLS // trade_count))


def probability_expectancy_positive(
    pnl: npt.ArrayLike, *, resamples: int, seed: int
) -> float:
    """Estimate P(mean PnL > 0) with an iid trade bootstrap."""
    values = np.asarray(pnl, dtype=np.float64)
    if values.size == 0:
        raise ValueError("bootstrap requires at least one observation")
    if resamples < 1:
        raise ValueError("resamples must be positive")
    rng = np.random.default_rng(seed)
    positive = 0
    chunk_size = bootstrap_chunk_size(values.size, resamples)
    completed = 0
    while completed < resamples:
        current = min(chunk_size, resamples - completed)
        indexes = rng.integers(0, values.size, size=(current, values.size))
        means = values[indexes].mean(axis=1)
        positive += int(np.count_nonzero(means > 0.0))
        completed += current
    return positive / resamples
