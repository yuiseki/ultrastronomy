"""The harness refuses, records and decides; these tests try to get past it."""

import json
import random

import pytest

from ultrastronomy import cli, fink, mission as M, synth
from ultrastronomy.gates import OVERCLAIM, run_gates
from ultrastronomy.run import lock, new_plan, plan_problems, read_json, write_json

DEMO_MISSION = {"id": "demo", "strata": ["Unknown", "SN candidate", "(SIMBAD) QSO"], "truth": [],
                "positive_groups": ["tde"]}


@pytest.fixture
def demo(tmp_path):
    assert cli.main(["demo", "--runs-dir", str(tmp_path)]) == 0
    return tmp_path / "demo-seed1"


def failed(run):
    return [g["gate"] for g in run_gates(run, DEMO_MISSION) if not g["passed"]]


def test_demo_passes_every_gate_and_is_reproducible(demo, tmp_path):
    assert failed(demo) == []
    first = read_json(demo / "results.json")
    assert cli.main(["demo", "--runs-dir", str(tmp_path)]) == 0
    second = read_json(demo / "results.json")
    assert first["recall_vs_load"] == second["recall_vs_load"]
    assert first["injection"] == second["injection"]


def test_empty_plan_cannot_be_locked(tmp_path):
    plan = new_plan(DEMO_MISSION, "20 minutes")
    problems = plan_problems(plan, DEMO_MISSION)
    assert any("claim" in p for p in problems)
    assert any("threshold" in p for p in problems)
    assert any("seed" in p for p in problems)
    write_json(tmp_path / "plan.json", plan)
    with pytest.raises(ValueError):
        lock(tmp_path, DEMO_MISSION)


def test_fetch_is_refused_before_the_plan_is_locked(tmp_path, capsys):
    run = tmp_path / "r"
    run.mkdir()
    write_json(run / "plan.json", new_plan(DEMO_MISSION, "20 minutes"))
    assert cli.main(["fetch", str(run), "--confirm"]) == 1
    assert "not locked" in capsys.readouterr().err
    assert not (run / "provenance.json").exists()


def test_a_plan_cannot_be_locked_twice_or_edited_after_the_lock(demo):
    with pytest.raises(ValueError):
        lock(demo, DEMO_MISSION)
    plan = read_json(demo / "plan.json")
    plan["decision_rule"]["threshold"] = 3
    write_json(demo / "plan.json", plan)
    assert "plan_locked" in failed(demo)
    assert cli.main(["evaluate", str(demo)]) == 1


def test_a_typed_number_that_differs_from_the_computed_one_fails(demo):
    claims = read_json(demo / "claims.json")
    claims[1]["value"] += 1
    write_json(demo / "claims.json", claims)
    assert failed(demo) == ["claims_traceable"]


def test_a_measured_claim_must_point_at_results(demo):
    write_json(demo / "claims.json", [{"kind": "measured", "text": "x", "evidence": "/nowhere", "value": 1}])
    assert failed(demo) == ["claims_traceable"]


def test_a_claim_without_a_kind_or_basis_fails(demo):
    write_json(demo / "claims.json", [{"kind": "inferred", "text": "probably a TDE"}])
    assert "claims_traceable" in failed(demo)


@pytest.mark.parametrize("sentence", [
    "We discovered a tidal disruption event.",
    "This is a confirmed TDE.",
    "A new transient was found at this position.",
    "This is the first detection of the flare.",
])
def test_announcement_words_fail_the_report(demo, sentence):
    with (demo / "report.md").open("a", encoding="utf-8") as fh:
        fh.write("\n" + sentence + "\n")
    assert failed(demo) == ["no_overclaim"]


def test_rediscovery_wording_is_allowed():
    assert not OVERCLAIM.search("A rediscovery test: 14 known objects were re-found; 2 candidates remain unchecked.")


def test_a_report_without_the_three_sections_fails(demo):
    (demo / "report.md").write_text("# Report\n\nAll good.\n", encoding="utf-8")
    assert failed(demo) == ["no_overclaim"]


def test_a_verdict_edited_by_hand_fails(demo):
    results = read_json(demo / "results.json")
    results["decision"]["verdict"] = "rejected"
    write_json(demo / "results.json", results)
    assert "verdict_by_rule" in failed(demo)


def test_missing_injection_fails(demo):
    results = read_json(demo / "results.json")
    results["injection"] = None
    write_json(demo / "results.json", results)
    assert failed(demo) == ["injection_recovery"]


def test_a_synthetic_run_is_never_exported(demo, tmp_path, capsys):
    assert cli.main(["export", str(demo), "--contributions-dir", str(tmp_path / "c")]) == 1
    assert "synthetic" in capsys.readouterr().err
    assert not (tmp_path / "c").exists()


def test_decide_follows_the_three_way_rule():
    assert M.decide(14, 19, 1, 112)["verdict"] == "supported"
    assert M.decide(2, 19, 30, 112)["verdict"] == "rejected"
    assert M.decide(3, 19, 12, 112)["verdict"] == "undecided"
    assert M.decide(3, 19, 0, 0)["verdict"] == "undecided"


def test_request_budget_stops_before_the_extra_request():
    budget = fink.Budget(2)
    budget.spend()
    budget.spend()
    with pytest.raises(fink.BudgetExceeded):
        budget.spend()


def test_planned_requests_counts_truth_weeks_and_objects():
    plan = new_plan(DEMO_MISSION, "x")
    plan["data"].update({"weeks": 3, "per_class": 2})
    mission = {"truth": [{}] * 23, "strata": ["a", "b", "c", "d", "e"]}
    assert M.planned_requests(plan, mission) == 23 + 15 + 30


def test_only_allow_listed_columns_are_requested():
    assert all(c.startswith("i:") for c in fink.COLUMNS)
    assert not any(c in fink.COLUMNS for c in ("d:tns", "d:cdsxmatch"))


def test_changed_data_is_refused(tmp_path):
    plan = new_plan(DEMO_MISSION, "x", source="synthetic")
    plan["data"]["seed"] = 3
    provenance, _ = M.fetch_synthetic(plan)
    provenance[0]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        M.load_objects(plan, provenance, tmp_path)


def test_injection_recovers_bright_flares_and_loses_faint_ones():
    inj = M.injection(seed=7, threshold=5, n_per_bin=60)
    by_mag = {b["peak_mag"]: b["recovery"] for b in inj["bins"]}
    assert by_mag[17.0] > 0.9
    assert by_mag[20.5] < 0.1
    assert by_mag[17.0] >= by_mag[19.0] >= by_mag[20.5]


def test_pool_counts_each_background_object_once(tmp_path):
    def results(ids):
        return {"data_source": "fink", "objects": [
            {"id": i, "role": "background", "label": "Unknown", "score": 5 if i == "a" else 1} for i in ids]}
    for name, ids in (("r1", ["a", "b"]), ("r2", ["b", "c"])):
        (tmp_path / name).mkdir()
        write_json(tmp_path / name / "results.json", results(ids))
    pooled = cli.pool(tmp_path)
    assert pooled["runs"] == 2 and pooled["background_objects"] == 3
    row = next(r for r in pooled["table"] if r["threshold"] == 5)
    assert row["background"]["Unknown"]["passed"] == 1 and row["background"]["Unknown"]["n"] == 3


def test_synthetic_supernovae_redden_and_flares_do_not():
    from ultrastronomy.lightcurve import light_curve_features
    rng = random.Random(11)
    sn = [light_curve_features(synth.sn_like(rng, synth.cadence(rng, 2459000.0, 900))) for _ in range(40)]
    tde = [light_curve_features(synth.tde_like(rng, synth.cadence(rng, 2459000.0, 900), 18.0)) for _ in range(40)]
    med = lambda fs: sorted(f["g_r_slope"] for f in fs if f and f["g_r_slope"] == f["g_r_slope"])
    assert med(sn)[len(med(sn)) // 2] > med(tde)[len(med(tde)) // 2]
