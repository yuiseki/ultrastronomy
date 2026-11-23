import math

from ultrastronomy.score import CRITERIA, tde_likeness


def base(**over):
    f = {
        "n_det": 40, "duration": 200.0, "g_r_peak": -0.2, "g_r_slope": 0.0,
        "dist_ps1": 0.2, "sgscore": 0.1,
    }
    f.update(over)
    return f


def test_a_blue_long_nuclear_flare_meets_every_criterion():
    assert tde_likeness(base()) == len(CRITERIA)


def test_each_failed_criterion_costs_one_point():
    full = len(CRITERIA)
    assert tde_likeness(base(sgscore=0.9)) == full - 1      # stellar host
    assert tde_likeness(base(dist_ps1=2.0)) == full - 1     # off-nuclear
    assert tde_likeness(base(g_r_peak=0.5)) == full - 1     # red at peak
    assert tde_likeness(base(g_r_slope=0.03)) == full - 1   # reddens like a supernova
    assert tde_likeness(base(duration=20.0)) == full - 1    # too short
    assert tde_likeness(base(n_det=3)) == full - 1          # too few points


def test_unknown_values_do_not_count_as_met():
    f = base(g_r_peak=math.nan, g_r_slope=math.nan, dist_ps1=math.nan, sgscore=math.nan)
    assert tde_likeness(f) == 2
