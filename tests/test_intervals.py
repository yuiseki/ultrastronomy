import pytest

from ultrastronomy.intervals import newcombe_difference, wilson


def test_wilson_matches_a_published_value():
    # Newcombe (1998), Statistics in Medicine 17, 857: 81 of 263 gives 0.2553 to 0.3662.
    lo, hi = wilson(81, 263)
    assert lo == pytest.approx(0.2553, abs=5e-4)
    assert hi == pytest.approx(0.3662, abs=5e-4)


def test_wilson_stays_inside_zero_and_one_at_the_edges():
    assert wilson(0, 10)[0] == 0.0
    assert wilson(10, 10)[1] == pytest.approx(1.0)
    assert wilson(0, 10)[1] > 0.0


def test_difference_matches_a_published_value():
    # Newcombe (1998), Statistics in Medicine 17, 873, example (a):
    # 56/70 against 48/80 gives +0.2000 with interval 0.0524 to 0.3339.
    d, lo, hi = newcombe_difference(56, 70, 48, 80)
    assert d == pytest.approx(0.2)
    assert lo == pytest.approx(0.0524, abs=5e-4)
    assert hi == pytest.approx(0.3339, abs=5e-4)


def test_equal_proportions_straddle_zero():
    d, lo, hi = newcombe_difference(5, 20, 25, 100)
    assert d == pytest.approx(0.0)
    assert lo < 0 < hi
