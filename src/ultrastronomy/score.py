"""A fixed, literature-based score for "looks like a tidal disruption event".

The thresholds follow the photometric selection used for the ZTF TDE sample
(van Velzen et al. 2021, ApJ 908, 4): a nuclear transient in a galaxy, blue
at peak, that does not redden as it fades, and lasts longer than a supernova.

The score was written before any light curve of the ground-truth objects was
looked at, and must stay that way: tuning it on those objects would turn the
evaluation into a measurement of the tuning.
"""

from __future__ import annotations

import math


def _lt(value, limit) -> bool:
    return value is not None and not math.isnan(value) and value < limit


def _ge(value, limit) -> bool:
    return value is not None and not math.isnan(value) and value >= limit


# name -> predicate over the feature dict
CRITERIA = {
    "galaxy_host": lambda f: _lt(f["sgscore"], 0.5),
    "nuclear": lambda f: _lt(f["dist_ps1"], 0.6),
    "blue_at_peak": lambda f: _lt(f["g_r_peak"], 0.0),
    "no_reddening": lambda f: _lt(f["g_r_slope"], 0.015),
    "long_lived": lambda f: _ge(f["duration"], 60.0),
    "well_sampled": lambda f: _ge(f["n_det"], 10),
}


def met(features) -> dict:
    return {name: bool(test(features)) for name, test in CRITERIA.items()}


def tde_likeness(features) -> int:
    """Number of criteria met. An unknown value counts as not met."""
    return sum(met(features).values())
