"""Light-curve features from ZTF alert photometry.

Input rows are Fink alert records (dicts keyed by `i:jd`, `i:fid`, ...).
Only positive difference-image detections are used: an alert with
`isdiffpos` false means the source got fainter than the reference image,
and its `magpsf` is the magnitude of the deficit, not of a brightening.

Alert photometry is the magnitude of the difference flux. For a transient
on a quiet host this is the transient itself; for a variable nucleus it is
the excess over the reference epoch.
"""

from __future__ import annotations

import math

import numpy as np

G, R = 1, 2
# Detections further apart than this belong to different flares. ZTF loses a
# field for about 100-150 days each year when it is behind the Sun, so a gap
# has to be longer than a season break before it means the source went quiet.
FLARE_GAP_DAYS = 250.0
# Window around the peak used for the colour at peak.
PEAK_WINDOW_DAYS = 15.0
# g and r detections closer than this are treated as simultaneous.
PAIR_DAYS = 1.5


def _is_positive(row) -> bool:
    return str(row.get("i:isdiffpos", "t")).lower() in ("t", "1", "true")


def _nanmedian(values) -> float:
    arr = np.array([v for v in values if v is not None], dtype=float)
    arr = arr[np.isfinite(arr)]
    # PS1 columns use -999 for "no match".
    arr = arr[arr > -900]
    return float(np.median(arr)) if arr.size else math.nan


def _colour_pairs(jd, fid, mag):
    """(time, g - r) for every g detection with an r detection within PAIR_DAYS."""
    g = fid == G
    r = fid == R
    if not g.any() or not r.any():
        return np.empty(0), np.empty(0)
    jr, mr = jd[r], mag[r]
    times, colours = [], []
    for t, m in zip(jd[g], mag[g]):
        k = int(np.argmin(np.abs(jr - t)))
        if abs(jr[k] - t) <= PAIR_DAYS:
            times.append((t + jr[k]) / 2)
            colours.append(m - mr[k])
    return np.array(times), np.array(colours)


def light_curve_features(rows) -> dict | None:
    rows = [r for r in rows if _is_positive(r) and r.get("i:magpsf") is not None]
    if not rows:
        return None
    rows.sort(key=lambda r: r["i:jd"])
    jd = np.array([r["i:jd"] for r in rows], dtype=float)
    fid = np.array([r["i:fid"] for r in rows], dtype=int)
    mag = np.array([r["i:magpsf"] for r in rows], dtype=float)

    # Split into flares at long gaps, and describe the flare holding the peak.
    breaks = np.flatnonzero(np.diff(jd) > FLARE_GAP_DAYS)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks + 1, [len(jd)]))
    i_peak = int(np.argmin(mag))
    seg = next((s, e) for s, e in zip(starts, ends) if s <= i_peak < e)
    s, e = seg
    t_peak = jd[i_peak]

    times, colours = _colour_pairs(jd[s:e], fid[s:e], mag[s:e])
    near = np.abs(times - t_peak) <= PEAK_WINDOW_DAYS
    if near.any():
        g_r_peak = float(np.median(colours[near]))
    elif colours.size:
        # No simultaneous pair at the peak: fall back to the closest pair.
        g_r_peak = float(colours[int(np.argmin(np.abs(times - t_peak)))])
    else:
        g_r_peak = math.nan
    after = times >= t_peak
    if after.sum() >= 3 and np.ptp(times[after]) > 0:
        g_r_slope = float(np.polyfit(times[after], colours[after], 1)[0])
    else:
        g_r_slope = math.nan

    return {
        "n_det": int(len(jd)),
        "n_flares": int(len(starts)),
        "total_span": float(jd[-1] - jd[0]),
        "duration": float(jd[e - 1] - jd[s]),
        "rise": float(t_peak - jd[s]),
        "decay": float(jd[e - 1] - t_peak),
        "peak_mag": float(mag[i_peak]),
        "amplitude": float(mag[s:e].max() - mag[s:e].min()),
        "t_peak": float(t_peak),
        "g_r_peak": g_r_peak,
        "g_r_slope": g_r_slope,
        "dist_ps1": _nanmedian(r.get("i:distpsnr1") for r in rows),
        "sgscore": _nanmedian(r.get("i:sgscore1") for r in rows),
    }
