import pytest

from ultrastronomy import mission as M


@pytest.fixture(autouse=True)
def fewer_injections(monkeypatch):
    """Ten injected flares per bin instead of a hundred: the tests check logic, not the curve."""
    real = M.injection
    monkeypatch.setattr(M, "injection", lambda seed, threshold, n_per_bin=10: real(seed, threshold, 10))
