import math

import numpy as np
import pytest

from ultrastronomy import periods


def sampled(period, amplitude, n=300, span=900.0, noise=0.02, seed=3):
    """A sinusoid observed at night only, a few times a week, with noise."""
    rng = np.random.default_rng(seed)
    nights = np.sort(rng.choice(int(span), size=n, replace=False))
    t = nights + rng.uniform(0.2, 0.45, size=n)
    y = 17.0 + amplitude * np.sin(2 * np.pi * t / period) + rng.normal(0, noise, size=n)
    return t, y


@pytest.mark.parametrize("period", [0.37, 2.9, 31.0])
def test_a_clear_sinusoid_is_found_at_its_period(period):
    t, y = sampled(period, 0.2)
    best = periods.best_period(t, y)
    assert periods.match(best["period"], period) == "exact"
    assert best["log10_fap"] < -10


def test_noise_alone_is_not_significant():
    t, y = sampled(1.7, 0.0)
    assert periods.best_period(t, y)["log10_fap"] > -3


def test_a_constant_offset_between_nights_is_not_read_as_a_one_day_period():
    # Brighter in the first half of each night: a systematic, not a star.
    t, y = sampled(1.7, 0.0, noise=0.005)
    y = y + 0.05 * (np.mod(t, 1.0) < 0.3)
    best = periods.best_period(t, y)
    assert abs(1 / best["period"] - round(1 / best["period"])) > periods.ALIAS_HALF_WIDTH or best["period"] > 1.01


def test_too_few_points_gives_no_answer():
    t, y = sampled(2.0, 0.2, n=30)
    assert periods.best_period(t, y) is None


def test_match_accepts_one_percent_and_the_first_harmonics():
    assert periods.match(1.005, 1.0) == "exact"
    assert periods.match(1.02, 1.0) == "none"
    assert periods.match(0.5, 1.0) == "harmonic"
    assert periods.match(2.01, 1.0) == "harmonic"
    assert periods.match(3.0, 1.0) == "none"


def test_power_follows_the_exponential_law_for_white_noise():
    rng = np.random.default_rng(0)
    t = np.sort(rng.uniform(0, 500, 400))
    freqs = np.linspace(0.05, 5, 4000)
    z = periods.lomb_scargle(t, rng.normal(0, 1, 400), freqs)
    assert z.mean() == pytest.approx(1.0, abs=0.1)
    assert (z > math.log(100)).mean() == pytest.approx(0.01, abs=0.01)
