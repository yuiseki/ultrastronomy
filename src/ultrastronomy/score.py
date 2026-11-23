"""Screen v1: six yes/no criteria for "looks like a tidal disruption event".

The idea comes from the photometric selection of the ZTF TDE sample
(van Velzen et al. 2021, ApJ 908, 4): a nuclear transient in a galaxy, blue
at peak, that does not redden as it fades. The thresholds here were written
from memory of that paper and have not been checked against it. `long_lived`
and `well_sampled` are simplifications of our own, not the paper's rise and
fade timescales.

Known weaknesses, left in place on purpose: the colour at peak falls back to
the nearest g/r pair however far away; a single outlier can become the peak;
`long_lived` has no upper limit, so a source seen over several seasons counts
as one long flare; the reddening slope is fitted over everything after the
peak. Fixing these after the known objects have been scored would be tuning.
A second version needs known objects that were not used to judge this one.
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
