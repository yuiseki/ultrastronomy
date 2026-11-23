"""The periods mission end to end, on a made-up sky served by a fake network."""

import json

import numpy as np
import pytest

from ultrastronomy import catalogues, cli, fink, mission as M
from ultrastronomy import mission_periods as MP
from ultrastronomy.gates import run_gates
from ultrastronomy.run import read_json, write_json

MISSION = M.load_mission("ztf-known-periods")


SKY = {}   # position of each fake catalogued star -> its period, filled as the fake VSX answers


def fake_get(url, params, budget, timeout=180.0):
    """VSX lists six variables per patch; IRSA returns a sinusoid at each, and noise elsewhere."""
    budget.spend()
    if url == catalogues.VSX:
        ra, dec = params["ra"], params["dec"]
        stars = [{"OID": str(100000 + int(ra * 100) * 10 + i), "Name": f"V{i}", "RA2000": str(ra + 0.01 * (i + 1)),
                  "Declination2000": str(dec + 0.01 * (i + 1)), "Period": str(0.3 + 0.7 * i), "MaxMag": "16.0 V",
                  "Discoverer": "ZTF" if i % 2 else "ASAS-SN", "Category": "Variable", "VariabilityType": "EW"}
                 for i in range(6)]
        for star in stars:
            SKY[(round(float(star["RA2000"]), 4), round(float(star["Declination2000"]), 4))] = float(star["Period"])
        stars.append({"OID": "99999999", "Name": "too new", "RA2000": str(ra), "Declination2000": str(dec),
                      "Period": "1.0", "MaxMag": "16.0 V", "Discoverer": "ASAS-SN", "Category": "Variable"})
        return json.dumps({"VSXObjects": {"VSXObject": stars}}).encode()
    _, ra, dec, radius = params["POS"].split()
    ra, dec, radius = float(ra), float(dec), float(radius)
    rng = np.random.default_rng(int(abs(ra * 1000 + dec * 7)) % 2**31)
    lines = ["oid,expid,hjd,mjd,mag,magerr,catflags,filtercode,ra,dec"]
    def curve(oid, period, cra, cdec):
        t = np.sort(rng.choice(900, size=200, replace=False)) + rng.uniform(0.2, 0.45, 200) + 58300
        mag = 16 + (0.2 * np.sin(2 * np.pi * t / period) if period else 0) + rng.normal(0, 0.02, 200)
        for a, b in zip(t, mag):
            lines.append(f"{oid},1,{a + 2400000.5},{a},{b:.4f},0.02,0,zr,{cra},{cdec}")
    if radius < 0.001:   # a catalogued star: a sinusoid at the period the fake VSX gave it
        curve(7000000 + int(ra * 10000) % 1000000, SKY[(round(ra, 4), round(dec, 4))], ra, dec)
    else:                # the background cone: five constant stars
        for k in range(5):
            curve(8000000 + int(ra * 100) * 10 + k, None, ra + 0.001 * k, dec)
    return "\n".join(lines).encode()


@pytest.fixture(scope="module")
def finished_run(tmp_path_factory):
    """One full run on the fake sky, made once: the search is slow."""
    root = tmp_path_factory.mktemp("periods")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(catalogues, "_get", fake_get)
        mp.setattr(fink, "PAUSE_SECONDS", 0)
        mp.setenv("ULTRA_CACHE", str(root / "cache"))
        mp.setattr(MP, "AMPLITUDES", [0.2])
        assert cli.main(["init", "p", "--mission", "ztf-known-periods", "--ai-budget", "test", "--runs-dir", str(root)]) == 0
        run = root / "p"
        plan = read_json(run / "plan.json")
        plan.update({"claim": "c", "rationale": "r", "failure_interpretation": "f", "seen_before_lock": "s",
                     "alternative_explanations": ["a"], "decision_rule": {"threshold": 5, "primary_stratum": "not catalogued"}})
        plan["data"].update({"seed": 4, "patches": 6, "per_stratum": 2, "max_requests": 60})
        write_json(run / "plan.json", plan)
        assert cli.main(["lock", str(run)]) == 0
        assert cli.main(["fetch", str(run), "--confirm"]) == 0
        assert cli.main(["evaluate", str(run)]) == 0
    write_json(run / "claims.json", [{"kind": "unverified", "text": "everything", "basis": "a fake sky"}])
    (run / "report.md").write_text("# Test\n\n## Measured\n\n" + (run / "measured.md").read_text() +
                                   "\n## Inferred\n\nNothing.\n\n## Not verified\n\n- Everything.\n")
    return run, root / "cache"


@pytest.fixture
def periods_run(finished_run, tmp_path, monkeypatch):
    """A private copy of the finished run, free to be tampered with."""
    import shutil
    run, cache = finished_run
    monkeypatch.setattr(MP, "AMPLITUDES", [0.2])
    monkeypatch.setattr(catalogues, "_get", fake_get)
    monkeypatch.setattr(fink, "PAUSE_SECONDS", 0)
    shutil.copytree(run, tmp_path / "p")
    return tmp_path / "p", cache


def failed(run, cache):
    return [g["gate"] for g in run_gates(run, MISSION, cache) if not g["passed"]]


def test_known_periods_are_found_and_constant_stars_are_not(periods_run):
    run, cache = periods_run
    results = read_json(run / "results.json")
    d = results["decision"]
    assert (d["positives_n"], d["background_n"]) == (12, 12)
    assert d["positives_passed"] == 12 and d["background_passed"] == 0
    assert d["verdict"] == "supported"
    assert results["injection"]["bins"][0] == {"amplitude": 0.2, "recovered": 12, "n": 12}
    assert failed(run, cache) == []


def test_entries_newer_than_the_cutoff_are_ignored(periods_run):
    run, _ = periods_run
    assert not any(o["id"] == "VSX-99999999" for o in read_json(run / "results.json")["objects"])


def test_the_two_catalogued_groups_are_kept_apart(periods_run):
    run, _ = periods_run
    labels = {o["label"] for o in read_json(run / "results.json")["objects"]}
    assert labels == {MP.ELSEWHERE, MP.BY_ZTF, MP.NOT_CATALOGUED}


def test_a_star_moved_between_groups_is_caught(periods_run):
    run, cache = periods_run
    provenance = read_json(run / "provenance.json")
    next(p for p in provenance if p["label"] == MP.BY_ZTF)["label"] = MP.ELSEWHERE
    write_json(run / "provenance.json", provenance)
    assert "sample_matches_plan" in failed(run, cache)


def test_a_dropped_star_is_caught(periods_run):
    run, cache = periods_run
    write_json(run / "provenance.json", read_json(run / "provenance.json")[1:])
    assert "sample_matches_plan" in failed(run, cache)


def test_an_edited_result_is_caught(periods_run):
    run, cache = periods_run
    results = read_json(run / "results.json")
    results["decision"]["background_passed"] = 0
    results["objects"][0]["match"] = "exact"
    results["injection"]["bins"][0]["recovered"] = 0
    write_json(run / "results.json", results)
    assert "results_recomputed" in failed(run, cache)


def test_without_the_data_the_record_is_not_verified(periods_run, tmp_path):
    run, _ = periods_run
    assert failed(run, tmp_path / "empty") == ["data_matches_provenance"]


def test_usable_filters_on_category_period_and_brightness():
    star = {"category": "Variable", "period": "0.5", "max_mag": "16.2 V"}
    assert MP._usable(star) == 0.5
    assert MP._usable({**star, "category": "Suspected"}) is None
    assert MP._usable({**star, "period": None}) is None
    assert MP._usable({**star, "period": "400"}) is None
    assert MP._usable({**star, "max_mag": "9.1 V"}) is None
    assert MP._usable({**star, "max_mag": "(0.3) r"}) is None


def test_patch_centres_are_repeatable_and_inside_the_footprint():
    a, b = MP.patch_centres(7, 50), MP.patch_centres(7, 50)
    assert a == b
    assert all(0 <= ra <= 360 and -20 <= dec <= 80 for ra, dec in a)


def test_a_star_seen_in_two_patches_is_taken_once(periods_run, monkeypatch):
    # Overlapping patches: the same catalogue entries and the same ZTF sources come back twice.
    run, cache = periods_run
    plan = read_json(run / "plan.json")
    monkeypatch.setattr(MP, "patch_centres", lambda seed, n: [(10.0, 10.0)] * n)
    items = MP.derive(plan, MISSION, cache / "overlap", fink.Budget(100))
    ids = [i["object_id"] for i in items]
    assert len(ids) == len(set(ids))
