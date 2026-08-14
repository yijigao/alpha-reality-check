import numpy as np
import pytest

from alpha_reality_check.bootstrap import probability_expectancy_positive


def test_bootstrap_is_deterministic_and_directional() -> None:
    values = np.array([1.0, 2.0, -0.25, 0.5])
    first = probability_expectancy_positive(values, resamples=500, seed=7)
    second = probability_expectancy_positive(values, resamples=500, seed=7)
    assert first == second
    assert 0.8 < first <= 1.0


def test_bootstrap_rejects_empty_and_bad_resamples() -> None:
    with pytest.raises(ValueError, match="at least one"):
        probability_expectancy_positive([], resamples=10, seed=1)
    with pytest.raises(ValueError, match="positive"):
        probability_expectancy_positive([1.0], resamples=0, seed=1)
