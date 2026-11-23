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
    """Scargle's normalised power: for white noise it follows exp(-z).

    `y` is one series, or several as columns sharing the same times. Several
    are searched in one pass, since the cost is in the sines and cosines of
    the times, not in the series.
    """
    series = y[:, None] if y.ndim == 1 else y
    series = series - series.mean(axis=0)
    variance = series.var(axis=0, ddof=1)
    out = np.empty((len(freqs), series.shape[1]))
    for start in range(0, len(freqs), CHUNK):
        phase = 2 * np.pi * freqs[start:start + CHUNK][:, None] * t
        c0, s0 = np.cos(phase), np.sin(phase)
        # Scargle's time offset tau, from the double-angle sums: tan(2 w tau) = sum sin(2wt) / sum cos(2wt).
        shift = 0.5 * np.arctan2((2 * c0 * s0).sum(1), (c0 * c0 - s0 * s0).sum(1))
        ct, st = np.cos(shift)[:, None], np.sin(shift)[:, None]
        c, s = c0 * ct + s0 * st, s0 * ct - c0 * st
        out[start:start + CHUNK] = 0.5 * ((c @ series) ** 2 / (c * c).sum(1)[:, None]
                                          + (s @ series) ** 2 / (s * s).sum(1)[:, None]) / variance
    return out[:, 0] if y.ndim == 1 else out


def best_periods(times, columns) -> list[dict | None]:
    """For each series on the same times: the strongest period and its false-alarm probability."""
    t = np.asarray(times, dtype=float)
    series = np.asarray(columns, dtype=float).T
    if len(t) < MIN_POINTS or np.ptp(t) <= 0:
        return [None] * series.shape[1]
    span = float(np.ptp(t))
    freqs = frequency_grid(span)
    usable = series.var(axis=0) > 0
    power = np.zeros((len(freqs), series.shape[1]))
    if usable.any():
        power[:, usable] = lomb_scargle(t, series[:, usable], freqs)
    independent = (F_MAX - F_MIN) * span
    out = []
    for k in range(series.shape[1]):
        if not usable[k]:
            out.append(None)
            continue
        i = int(np.argmax(power[:, k]))
        z = float(power[i, k])
        # 1 - (1 - e^-z)^M, written so that it does not round to zero or one.
        log10_fap = math.log10(max(-math.expm1(independent * math.log1p(-math.exp(-z))), 1e-300))
        out.append({"period": float(1.0 / freqs[i]), "power": z, "log10_fap": log10_fap, "n_points": int(len(t))})
    return out


def best_period(times, mags) -> dict | None:
    """The strongest period of one series, or None with too few points."""
    return best_periods(times, [mags])[0]


def match(found: float, catalogued: float) -> str:
    """exact, harmonic (half or double: usual for eclipsing binaries), or none."""
    ratio = found / catalogued
    if abs(ratio - 1) <= TOLERANCE:
        return "exact"
    if abs(ratio - 0.5) <= 0.5 * TOLERANCE or abs(ratio - 2) <= 2 * TOLERANCE:
        return "harmonic"
    return "none"
