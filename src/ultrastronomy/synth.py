"""Synthetic alert light curves, for the offline demo and for injection tests.

Everything here is made up from simple formulas. It is useful for checking
that the pipeline behaves, and for asking "how faint could a flare be and
still pass the screen under this cadence model". It says nothing about the
real sky, and the cadence model is a simplification, not ZTF's schedule.
"""

from __future__ import annotations

import math
import random

G, R = 1, 2
LIMITING_MAG = 20.5
CADENCE_MODEL = (
    "each band observed on a third of nights during a 240-day season, "
    "30% of visits lost to weather, limiting magnitude 20.5 with 0.3 mag scatter"
)


def cadence(rng: random.Random, start: float, days: int) -> list[tuple[float, int]]:
    """Observation epochs (jd, band) under the simplified cadence model."""
    season_start = rng.uniform(0, 365)
    epochs = []
    for d in range(days):
        if ((d - season_start) % 365) >= 240:
            continue
        for band in (G, R):
            if rng.random() < (1 / 3) * 0.7:
                epochs.append((start + d + rng.uniform(0, 0.3), band))
    return epochs


def _sigma(mag: float) -> float:
    return min(0.3, max(0.02, 0.2 * 10 ** (0.4 * (mag - LIMITING_MAG))))


def _alert(rng, jd, band, mag, positive=True, **host) -> dict | None:
    """One alert, or None when the source is below that night's limit."""
    if mag > LIMITING_MAG + rng.gauss(0, 0.3):
        return None
    sig = _sigma(mag)
    row = {"i:jd": jd, "i:fid": band, "i:magpsf": mag + rng.gauss(0, sig), "i:sigmapsf": sig,
           "i:isdiffpos": "t" if positive else "f"}
    row.update(host)
    return row


def _rows(alerts) -> list[dict]:
    return [a for a in alerts if a is not None]


def tde_like(rng, epochs, peak_mag, host=None) -> list[dict]:
    """Gaussian rise, t^-5/3 decay, constant blue colour: the textbook TDE shape."""
    host = host or {"i:distpsnr1": abs(rng.gauss(0.2, 0.08)), "i:sgscore1": rng.uniform(0, 0.3)}
    t_peak = epochs[0][0] + rng.uniform(0.25, 0.6) * (epochs[-1][0] - epochs[0][0])
    rise, t0 = rng.uniform(10, 30), rng.uniform(30, 90)
    colour = rng.gauss(-0.25, 0.08)
    out = []
    for jd, band in epochs:
        dt = jd - t_peak
        frac = math.exp(-dt * dt / (2 * rise * rise)) if dt < 0 else ((dt + t0) / t0) ** (-5 / 3)
        if frac <= 1e-4:
            continue
        mag = peak_mag - 2.5 * math.log10(frac) - (colour if band == R else 0.0)
        out.append(_alert(rng, jd, band, mag, **host))
    return _rows(out)


def sn_like(rng, epochs) -> list[dict]:
    """Fast rise, exponential decay, reddening after the peak; often off-centre."""
    host = {"i:distpsnr1": abs(rng.gauss(1.2, 1.0)), "i:sgscore1": rng.uniform(0, 0.4)}
    t_peak = epochs[0][0] + rng.uniform(0.2, 0.8) * (epochs[-1][0] - epochs[0][0])
    rise, tau, peak = rng.uniform(6, 14), rng.uniform(20, 45), rng.uniform(17.5, 19.8)
    out = []
    for jd, band in epochs:
        dt = jd - t_peak
        frac = math.exp(-dt * dt / (2 * rise * rise)) if dt < 0 else math.exp(-dt / tau)
        if frac <= 1e-3:
            continue
        colour = -0.1 + (min(1.0, 0.02 * dt) if dt > 0 else 0.0)
        mag = peak - 2.5 * math.log10(frac) - (colour if band == R else 0.0)
        out.append(_alert(rng, jd, band, mag, **host))
    return _rows(out)


def agn_like(rng, epochs) -> list[dict]:
    """A nuclear source wandering around its reference brightness, both signs."""
    host = {"i:distpsnr1": abs(rng.gauss(0.15, 0.06)), "i:sgscore1": rng.uniform(0, 1)}
    tau, colour = rng.uniform(100, 400), rng.gauss(0.0, 0.2)
    x, last, out = rng.gauss(0, 1), epochs[0][0], []
    for jd, band in epochs:
        decay = math.exp(-(jd - last) / tau)
        x, last = x * decay + rng.gauss(0, math.sqrt(max(0.0, 1 - decay * decay))), jd
        mag = 20.2 - 2.5 * math.log10(abs(x) + 1e-3) - (colour if band == R else 0.0)
        out.append(_alert(rng, jd, band, mag, positive=x > 0, **host))
    return _rows(out)


def variable_star(rng, epochs) -> list[dict]:
    host = {"i:distpsnr1": abs(rng.gauss(0.1, 0.05)), "i:sgscore1": rng.uniform(0.85, 1.0)}
    period, phase, colour = rng.uniform(0.3, 300), rng.uniform(0, 6.28), rng.gauss(0.6, 0.3)
    out = []
    for jd, band in epochs:
        x = math.sin(2 * math.pi * jd / period + phase)
        mag = 19.8 - 2.5 * math.log10(abs(x) + 1e-3) - (colour if band == R else 0.0)
        out.append(_alert(rng, jd, band, mag, positive=x > 0, **host))
    return _rows(out)


def junk(rng, epochs) -> list[dict]:
    """One to three isolated detections: artefacts, cosmic rays, asteroids."""
    host = {"i:distpsnr1": rng.uniform(0, 5), "i:sgscore1": rng.uniform(0, 1)}
    picks = rng.sample(epochs, k=min(len(epochs), rng.randint(1, 3)))
    return _rows(_alert(rng, jd, band, rng.uniform(18, 20.3), **host) for jd, band in picks)


# Demo strata: which generators stand in for which Fink class.
DEMO_STRATA = {
    "Unknown": (variable_star, junk),
    "SN candidate": (sn_like,),
    "(SIMBAD) QSO": (agn_like,),
}


def demo_population(seed: int, n_positive: int = 20, n_per_stratum: int = 60):
    """(objects, truth, background) for the offline demo. All synthetic."""
    rng = random.Random(seed)
    objects, truth, background = {}, [], []
    for i in range(n_positive):
        oid = f"SYN-TDE-{i:03d}"
        objects[oid] = tde_like(rng, cadence(rng, 2459000.0, 900), rng.uniform(17.5, 20.2))
        truth.append({"ztf_id": oid, "tns_name": "", "group": "tde"})
    for stratum, generators in DEMO_STRATA.items():
        for i in range(n_per_stratum):
            oid = f"SYN-{stratum.split()[-1].upper()}-{i:03d}"
            objects[oid] = rng.choice(generators)(rng, cadence(rng, 2459000.0, 900))
            background.append({"ztf_id": oid, "stratum": stratum})
    return objects, truth, background
