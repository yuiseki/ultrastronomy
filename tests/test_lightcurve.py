import math

import pytest

from ultrastronomy.lightcurve import light_curve_features


def alert(jd, fid, mag, sig=0.05, **extra):
    row = {"i:jd": jd, "i:fid": fid, "i:magpsf": mag, "i:sigmapsf": sig, "i:isdiffpos": "t"}
    row.update(extra)
    return row


def flare(fid, t0, rise, decay, base=20.0, depth=2.0, offset=0.0):
    """One flare sampled every 5 days: linear rise to the peak, linear decay back."""
    rows = []
    t = t0
    while t <= t0 + rise + decay:
        if t <= t0 + rise:
            frac = (t - t0) / rise
        else:
            frac = 1 - (t - t0 - rise) / decay
        rows.append(alert(t, fid, base - depth * frac + offset))
        t += 5
    return rows


def test_empty_light_curve_has_no_features():
    assert light_curve_features([]) is None


def test_negative_subtractions_are_ignored():
    rows = flare(1, 0, 20, 80) + [alert(50, 1, 15.0, **{"i:isdiffpos": "f"})]
    f = light_curve_features(rows)
    # The 15.0 mag point is a negative difference, so it must not become the peak.
    assert f["peak_mag"] == pytest.approx(18.0)


def test_duration_rise_and_decay_of_a_single_flare():
    f = light_curve_features(flare(1, 1000, 20, 80))
    assert f["n_det"] == 21
    assert f["duration"] == pytest.approx(100)
    assert f["rise"] == pytest.approx(20)
    assert f["decay"] == pytest.approx(80)
    assert f["amplitude"] == pytest.approx(2.0)


def test_colour_is_g_minus_r_around_the_peak():
    # g (fid 1) is 0.3 mag brighter than r (fid 2): a blue transient.
    rows = flare(1, 0, 20, 80) + flare(2, 0, 20, 80, offset=0.3)
    f = light_curve_features(rows)
    assert f["g_r_peak"] == pytest.approx(-0.3, abs=0.02)


def test_colour_is_nan_with_a_single_band():
    f = light_curve_features(flare(1, 0, 20, 80))
    assert math.isnan(f["g_r_peak"])


def test_colour_drift_separates_cooling_from_constant_colour():
    constant = flare(1, 0, 20, 200) + flare(2, 0, 20, 200, offset=0.3)
    f_const = light_curve_features(constant)
    assert abs(f_const["g_r_slope"]) < 1e-4

    # g fades faster than r after the peak: the transient reddens, like a supernova.
    reddening = flare(1, 0, 20, 200, depth=3.0) + flare(2, 0, 20, 200, depth=1.0)
    f_red = light_curve_features(reddening)
    assert f_red["g_r_slope"] > 0.005


def test_number_of_flares_counts_separate_brightenings():
    one = light_curve_features(flare(1, 0, 20, 80))
    two = light_curve_features(flare(1, 0, 20, 80) + flare(1, 600, 20, 80))
    assert one["n_flares"] == 1
    assert two["n_flares"] == 2


def test_host_columns_take_the_median_over_alerts():
    rows = [
        alert(0, 1, 19.0, **{"i:distpsnr1": 0.2, "i:sgscore1": 0.1}),
        alert(5, 1, 18.5, **{"i:distpsnr1": 0.4, "i:sgscore1": 0.1}),
        alert(10, 1, 19.0, **{"i:distpsnr1": 0.3, "i:sgscore1": 0.3}),
    ]
    f = light_curve_features(rows)
    assert f["dist_ps1"] == pytest.approx(0.3)
    assert f["sgscore"] == pytest.approx(0.1)


def test_missing_host_columns_become_nan():
    f = light_curve_features(flare(1, 0, 20, 80))
    assert math.isnan(f["dist_ps1"])
    assert math.isnan(f["sgscore"])
