"""Period search on an unevenly sampled light curve: the Lomb-Scargle periodogram.

Nothing here is new. The periodogram is Scargle (1982, ApJ 263, 835); the
false-alarm probability is his formula for white noise, with the number of
independent frequencies taken as the frequency span times the time span.
Real photometry is not white noise, so that probability is too optimistic.
The mission measures by how much, on stars not catalogued as variable.
"""

from __future__ import annotations

import math

import numpy as np

MIN_POINTS = 50
F_MIN, F_MAX = 1 / 100.0, 10.0     # cycles per day: periods from 0.1 to 100 days
OVERSAMPLE = 3
# A ground-based survey observes at night, so anything constant in the data
# shows up at one cycle per day and its multiples. Those frequencies are left out.
ALIAS_HALF_WIDTH = 0.005
TOLERANCE = 0.01                   # a period within 1% counts as the same period
CHUNK = 1000


def frequency_grid(span_days: float) -> np.ndarray:
    step = 1.0 / (OVERSAMPLE * span_days)
    freqs = np.arange(F_MIN, F_MAX, step)
    nearest = np.rint(freqs)
    return freqs[(nearest < 1) | (np.abs(freqs - nearest) > ALIAS_HALF_WIDTH)]


def lomb_scargle(t: np.ndarray, y: np.ndarray, freqs: np.ndarray) -> np.ndarray:
    """Scargle's normalised power: for white noise it follows exp(-z)."""
    y = y - y.mean()
    variance = y.var(ddof=1)
    out = np.empty(len(freqs))
    for start in range(0, len(freqs), CHUNK):
        omega = 2 * np.pi * freqs[start:start + CHUNK][:, None]
        tau = np.arctan2(np.sin(2 * omega * t).sum(1), np.cos(2 * omega * t).sum(1))[:, None] / (2 * omega)
        c, s = np.cos(omega * (t - tau)), np.sin(omega * (t - tau))
        out[start:start + CHUNK] = 0.5 * ((c @ y) ** 2 / (c * c).sum(1) + (s @ y) ** 2 / (s * s).sum(1)) / variance
    return out


def best_period(times, mags) -> dict | None:
    """The strongest period and its false-alarm probability, or None with too few points."""
    t, y = np.asarray(times, dtype=float), np.asarray(mags, dtype=float)
    if len(t) < MIN_POINTS or np.ptp(t) <= 0 or y.var() == 0:
        return None
    span = float(np.ptp(t))
    freqs = frequency_grid(span)
    power = lomb_scargle(t, y, freqs)
    i = int(np.argmax(power))
    z = float(power[i])
    independent = (F_MAX - F_MIN) * span
    # 1 - (1 - e^-z)^M, written so that it does not round to zero or one.
    log10_fap = math.log10(max(-math.expm1(independent * math.log1p(-math.exp(-z))), 1e-300))
    return {"period": float(1.0 / freqs[i]), "power": z, "log10_fap": log10_fap, "n_points": int(len(t))}


def match(found: float, catalogued: float) -> str:
    """exact, harmonic (half or double: usual for eclipsing binaries), or none."""
    ratio = found / catalogued
    if abs(ratio - 1) <= TOLERANCE:
        return "exact"
    if abs(ratio - 0.5) <= 0.5 * TOLERANCE or abs(ratio - 2) <= 2 * TOLERANCE:
        return "harmonic"
    return "none"
