"""The harness refuses, records and decides; these tests try to get past it.

Many of the cases come from an independent review that got 24 of 31
tampered records through the first version of the gates. Each of those is
kept here so that it stays caught.
"""

import random
import shutil

import pytest

from ultrastronomy import cli, fink, mission as M, synth
from ultrastronomy.gates import ANNOUNCEMENT, _plain, report_sections, run_gates
from ultrastronomy.run import file_sha256, lock, new_plan, plan_problems, read_json, write_json

DEMO = M.load_mission("demo")


@pytest.fixture
def demo(tmp_path):
    assert cli.main(["demo", "--runs-dir", str(tmp_path)]) == 0
    return tmp_path / "demo-seed1"


def failed(run):
    return [g["gate"] for g in run_gates(run, DEMO) if not g["passed"]]


def append_to_section(run, heading, text):
    report = (run / "report.md").read_text(encoding="utf-8")
    marker = f"## {heading}\n"
    assert marker in report
    (run / "report.md").write_text(report.replace(marker, marker + "\n" + text + "\n", 1), encoding="utf-8")


# --- the honest path


def test_demo_passes_every_gate_and_is_reproducible(demo, tmp_path):
    assert failed(demo) == []
    first = read_json(demo / "results.json")
    assert cli.main(["demo", "--runs-dir", str(tmp_path)]) == 0
    assert read_json(demo / "results.json") == first


# --- the plan and its lock


def test_empty_plan_cannot_be_locked(tmp_path):
    plan = new_plan(DEMO, "20 minutes")
    problems = plan_problems(plan, DEMO)
    assert any("claim" in p for p in problems)
    assert any("threshold" in p for p in problems)
    assert any("seed" in p for p in problems)
    write_json(tmp_path / "plan.json", plan)
    with pytest.raises(ValueError):
        lock(tmp_path, DEMO)


def test_fetch_is_refused_before_the_plan_is_locked(tmp_path, capsys):
    run = tmp_path / "r"
    run.mkdir()
    plan = new_plan(DEMO, "20 minutes")
    write_json(run / "plan.json", plan)
    assert cli.main(["fetch", str(run), "--confirm"]) == 1
    assert "not locked" in capsys.readouterr().err
    assert not (run / "provenance.json").exists()
    assert "fetch_refused" in (run / "log.jsonl").read_text()


def test_a_plan_edited_after_the_lock_is_caught(demo):
    plan = read_json(demo / "plan.json")
    plan["decision_rule"]["threshold"] = 3
    write_json(demo / "plan.json", plan)
    assert "plan_locked" in failed(demo)
    assert cli.main(["evaluate", str(demo)]) == 1


def test_relocking_after_seeing_results_is_caught(demo):
    # Review finding G3: delete the lock, change the plan, lock again.
    (demo / "plan.lock").unlink()
    plan = read_json(demo / "plan.json")
    plan["decision_rule"]["threshold"] = 4
    write_json(demo / "plan.json", plan)
    lock(demo, DEMO)
    assert cli.main(["fetch", str(demo)]) == 0
    assert cli.main(["evaluate", str(demo)]) == 0
    assert "locked_once_before_data" in failed(demo)


def test_a_lock_hash_rewritten_by_hand_still_fails_on_recomputation(demo):
    # Review finding G3: edit the plan and recompute plan_sha256 in plan.lock.
    plan = read_json(demo / "plan.json")
    plan["decision_rule"]["threshold"] = 2
    write_json(demo / "plan.json", plan)
    record = read_json(demo / "plan.lock")
    record["plan_sha256"] = file_sha256(demo / "plan.json")
    write_json(demo / "plan.lock", record)
    assert "results_recomputed" in failed(demo)


def test_a_backdated_or_malformed_timestamp_is_caught(demo):
    provenance = read_json(demo / "provenance.json")
    provenance[0]["accessed_at"] = "not-a-date-but-sorts-late"
    write_json(demo / "provenance.json", provenance)
    assert "read_after_lock" in failed(demo)


def test_changed_mission_files_are_caught(demo, tmp_path):
    folder = tmp_path / "missions" / "demo"
    shutil.copytree(DEMO["dir"], folder)
    mission = M.load_mission("demo", tmp_path / "missions")
    assert not [g for g in run_gates(demo, mission) if g["gate"] == "code_unchanged" and not g["passed"]]
    data = read_json(folder / "mission.json")
    data["positive_groups"] = []
    write_json(folder / "mission.json", data)
    mission = M.load_mission("demo", tmp_path / "missions")
    assert "code_unchanged" in [g["gate"] for g in run_gates(demo, mission) if not g["passed"]]


# --- numbers


@pytest.mark.parametrize("edit", [
    lambda r: r["decision"].update(positives_passed=20, positives_n=20, background_n=100000),
    lambda r: r["decision"].update(ci95_low=0.9, ci95_high=0.99),
    lambda r: r["decision"].update(verdict="rejected"),
    lambda r: [o.update(score=6) for o in r["objects"] if o["role"] == "truth"],
    lambda r: r["objects"].append({"id": "ZTF99zzzzzzz", "role": "background", "label": "Unknown", "score": 0,
                                   "met": {}, "no_positive_detection": True, "n_det": 0}),
    lambda r: [b.update(recovered=100, recovery=1.0) for b in r["injection"]["bins"]],
    lambda r: r["injection"].update(bins=[]),
    lambda r: r.update(injection=None),
], ids=["counts", "interval", "verdict", "scores", "invented-object", "injection-100%", "injection-empty", "no-injection"])
def test_results_edited_by_hand_are_caught(demo, edit):
    # Review finding G1: every one of these passed the first gates.
    results = read_json(demo / "results.json")
    edit(results)
    write_json(demo / "results.json", results)
    assert "results_recomputed" in failed(demo)


def test_forged_provenance_hash_is_caught(demo):
    provenance = read_json(demo / "provenance.json")
    provenance[0]["sha256"] = "0" * 64
    write_json(demo / "provenance.json", provenance)
    assert failed(demo) == ["data_matches_provenance"]


def test_a_record_without_its_data_is_not_verified(tmp_path):
    # Review finding G2: a missing cache used to skip the check and pass.
    plan = new_plan(DEMO, "x")
    plan["data"]["seed"] = 1
    with pytest.raises(FileNotFoundError):
        M.load_objects(plan, [{"object_id": "ZTF20aaaaaaa", "sha256": "0" * 64}], tmp_path)


def test_numbers_typed_into_the_measured_section_are_caught(demo):
    # Review finding G4.
    append_to_section(demo, "Measured", "- Supported at 12 sigma: 20 of 20, against 0 of 100000.")
    assert failed(demo) == ["measured_is_generated"]


def test_measured_claims_cannot_be_written_by_the_agent(demo):
    # Review finding G5: a true number under a false sentence.
    claims = read_json(demo / "claims.json")
    claims.append({"kind": "measured", "text": "Real TDEs found on the sky.", "evidence": "/decision/positives_passed", "value": 16})
    write_json(demo / "claims.json", claims)
    assert failed(demo) == ["claims_labelled"]


def test_claims_need_a_kind_a_basis_and_something_unverified(demo):
    write_json(demo / "claims.json", [{"kind": "inferred", "text": "probably a TDE"}])
    assert "claims_labelled" in failed(demo)
    write_json(demo / "claims.json", [{"kind": "inferred", "text": "x", "basis": "y"}])
    assert "claims_labelled" in failed(demo)


# --- the report


def test_sections_hidden_in_a_comment_do_not_count(demo):
    (demo / "report.md").write_text("<!-- ## Measured ## Inferred ## Not verified -->\nAll good.\n", encoding="utf-8")
    assert {"measured_is_generated", "report_structure"} <= set(failed(demo))


def test_sections_must_be_the_three_in_order():
    assert [h for h, _ in report_sections("## Measured\na\n## Inferred\nb\n## Not verified\nc\n")] == ["Measured", "Inferred", "Not verified"]


def test_an_object_named_under_inferred_is_caught(demo):
    append_to_section(demo, "Inferred", "SYN-QSO-003 is probably a tidal disruption event at z=0.05.")
    assert failed(demo) == ["report_structure"]


@pytest.mark.parametrize("sentence", [
    "We discovered a tidal disruption event.",
    "We are discovering a tidal disruption event that nobody has catalogued.",
    "This is a confirmed TDE.",
    "A new transient was found at this position.",
    "This is the first detection of the flare.",
    "It is a previously unknown tidal disruption event, found by this run.",
    "We identified a novel transient.",
    "A newly identified TDE, detected here for the first time.",
    "We report a new, bona fide TDE.",
    "It was verified as a genuine tidal disruption event. Proven beyond doubt.",
    "We dis​covered a flare.",
    "We dis**covered** a flare.",
    "A new  object appeared.",
])
def test_announcement_wording_is_linted(demo, sentence):
    # Review finding G6. The lint is a tripwire; these are the evasions it now knows.
    append_to_section(demo, "Not verified", sentence)
    assert failed(demo) == ["wording_lint"]


def test_announcement_wording_in_any_claim_field_is_linted(demo):
    claims = read_json(demo / "claims.json")
    claims[0]["basis"] = "We discovered a new TDE and confirmed it."
    write_json(demo / "claims.json", claims)
    assert failed(demo) == ["wording_lint"]


def test_the_lint_lets_plain_rediscovery_wording_through():
    for text in ["A rediscovery test: 14 known objects were re-found.", "Two objects passed the screen and were not examined."]:
        assert not ANNOUNCEMENT.search(_plain(text))


# --- export and pooling


def test_a_synthetic_run_is_never_exported(demo, tmp_path, capsys):
    assert cli.main(["export", str(demo), "--contributions-dir", str(tmp_path / "c")]) == 1
    assert "synthetic" in capsys.readouterr().err
    assert not (tmp_path / "c").exists()


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


# --- the decision rule


def test_the_rule_is_symmetric_and_needs_enough_objects():
    assert M.decide(14, 19, 1, 112)["verdict"] == "supported"
    assert M.decide(1, 19, 80, 112)["verdict"] == "rejected"
    # Review finding S2: no difference is not a rejection.
    assert M.decide(6, 19, 36, 112)["verdict"] == "undecided"
    assert M.decide(0, 19, 0, 112)["verdict"] == "undecided"
    # Review finding S2: two objects cannot support anything.
    small = M.decide(2, 2, 0, 2)
    assert small["verdict"] == "undecided" and "fewer than" in small["reason"]
    assert M.decide(14, 19, 0, 4)["verdict"] == "undecided"


def test_equal_true_rates_rarely_give_a_verdict():
    rng = random.Random(5)
    verdicts = [M.decide(sum(rng.random() < 0.3 for _ in range(19)), 19,
                         sum(rng.random() < 0.3 for _ in range(30)), 30)["verdict"] for _ in range(2000)]
    assert verdicts.count("undecided") / len(verdicts) > 0.9


# --- budgets and columns


def test_request_budget_stops_before_the_extra_request():
    budget = fink.Budget(2)
    budget.spend()
    budget.spend()
    with pytest.raises(fink.BudgetExceeded):
        budget.spend()


def test_requests_spent_adds_up_over_attempts(tmp_path):
    # Review finding G9: the budget used to restart with every call.
    (tmp_path / "log.jsonl").write_text(
        '{"event": "fetch_failed", "requests_used": 10}\n{"event": "fetch_failed", "requests_used": 10}\n{"event": "lock"}\n')
    assert M.requests_spent(tmp_path) == 20


def test_a_plan_that_cannot_fit_its_budget_is_not_locked(tmp_path, capsys):
    run = tmp_path / "r"
    run.mkdir()
    mission = M.load_mission("ztf-nuclear-transients")
    plan = new_plan(mission, "x")
    plan.update({"claim": "c", "rationale": "r", "failure_interpretation": "f", "seen_before_lock": "s",
                 "alternative_explanations": ["a"], "decision_rule": {"threshold": 5, "primary_stratum": "Unknown"}})
    plan["data"].update({"seed": 1, "max_requests": 10})
    write_json(run / "plan.json", plan)
    assert cli.main(["lock", str(run)]) == 1
    assert "max_requests" in capsys.readouterr().err


def test_planned_requests_counts_truth_weeks_and_objects():
    plan = new_plan(DEMO, "x")
    plan["data"].update({"weeks": 3, "per_class": 2})
    assert M.planned_requests(plan, {"truth": [{}] * 23, "strata": ["a", "b", "c", "d", "e"]}) == 23 + 15 + 30


def test_only_allow_listed_columns_are_requested():
    assert all(c.startswith("i:") for c in fink.COLUMNS)
    assert not any(c in fink.COLUMNS for c in ("d:tns", "d:cdsxmatch"))


def test_a_date_becomes_the_right_julian_date():
    assert fink.date_to_jd("2020-05-31") == pytest.approx(2459000.5)


# --- synthetic data and injection


def test_injection_recovers_bright_flares_and_loses_faint_ones():
    inj = M.injection(seed=7, threshold=5, n_per_bin=60)
    by_mag = {b["peak_mag"]: b["recovery"] for b in inj["bins"]}
    assert by_mag[17.0] > 0.9
    assert by_mag[20.5] < 0.1
    assert by_mag[17.0] >= by_mag[19.0] >= by_mag[20.5]


def test_synthetic_supernovae_redden_and_flares_do_not():
    from ultrastronomy.lightcurve import light_curve_features
    rng = random.Random(11)
    sn = [light_curve_features(synth.sn_like(rng, synth.cadence(rng, 2459000.0, 900))) for _ in range(40)]
    tde = [light_curve_features(synth.tde_like(rng, synth.cadence(rng, 2459000.0, 900), 18.0)) for _ in range(40)]
    slopes = lambda fs: sorted(f["g_r_slope"] for f in fs if f and f["g_r_slope"] == f["g_r_slope"])
    assert slopes(sn)[len(slopes(sn)) // 2] > slopes(tde)[len(slopes(tde)) // 2]


# --- second review: a free model got nine edited records through the rebuilt gates.
#     Most went through provenance.json, which the gates used to trust.


def reevaluate(run):
    assert cli.main(["evaluate", str(run)]) == 0
    (run / "report.md").write_text(
        f"# Run {run.name}\n\n## Measured\n\n" + (run / "measured.md").read_text(encoding="utf-8") +
        "\n## Inferred\n\nNothing.\n\n## Not verified\n\n- Everything.\n", encoding="utf-8")


def edit_provenance(run, edit):
    provenance = read_json(run / "provenance.json")
    provenance = edit(provenance) or provenance
    write_json(run / "provenance.json", provenance)
    reevaluate(run)


def test_relabelling_failed_positives_is_caught(demo):
    low = {o["id"] for o in read_json(demo / "results.json")["objects"] if o["role"] == "truth" and o["score"] < 5}
    assert low
    edit_provenance(demo, lambda p: [x.update(label="sn") for x in p if x["object_id"] in low] and None)
    assert failed(demo) == ["sample_matches_plan"]


def test_dropping_a_stratum_is_caught(demo):
    edit_provenance(demo, lambda p: [x for x in p if x["label"] != "(SIMBAD) QSO"])
    assert failed(demo) == ["sample_matches_plan"]


def test_duplicated_objects_are_caught(demo):
    edit_provenance(demo, lambda p: p + [dict(p[0])] * 9)
    assert failed(demo) == ["sample_matches_plan"]


def test_text_smuggled_into_measured_through_a_label_is_caught(demo):
    def edit(p):
        p[-1]["label"] = "Unknown` objects passing: 60 of 60.\n- A new class of transients was found.\n- `Unknown"
    edit_provenance(demo, edit)
    assert "sample_matches_plan" in failed(demo)


def test_an_edited_measured_md_is_caught(demo):
    path = demo / "measured.md"
    path.write_text(path.read_text(encoding="utf-8").replace("supported", "rejected"), encoding="utf-8")
    assert failed(demo) == ["measured_is_generated"]


def test_text_before_the_first_heading_is_caught(demo):
    report = (demo / "report.md").read_text(encoding="utf-8")
    (demo / "report.md").write_text(report.replace("## Measured", "The screen kept all 20 of 20.\n\n## Measured", 1), encoding="utf-8")
    assert failed(demo) == ["report_structure"]


def test_html_in_the_report_is_caught(demo):
    append_to_section(demo, "Inferred", "<h2>Measured</h2>\n\nPositives passing: 20 of 20.")
    assert failed(demo) == ["report_structure"]


def test_an_object_id_split_by_markdown_is_caught(demo):
    append_to_section(demo, "Inferred", "SYN-**QSO**-003 looks like a flare.")
    assert failed(demo) == ["report_structure"]


def test_an_object_named_in_an_inferred_claim_is_caught(demo):
    claims = read_json(demo / "claims.json")
    claims[0]["basis"] = "SYN-QSO-003 scored 6."
    write_json(demo / "claims.json", claims)
    assert failed(demo) == ["claims_labelled"]


def test_the_gate_derives_the_same_sample_as_the_fetch(tmp_path, monkeypatch):
    """`gates.expected_sample` repeats the selection in `mission.fetch_fink`. Keep them in step."""
    from ultrastronomy.pipelines import Screen
    mission = M.load_mission("ztf-nuclear-transients")
    plan = new_plan(mission, "x")
    plan["data"].update({"seed": 42, "weeks": 2, "per_class": 2, "max_requests": 200})

    def fake_post(endpoint, payload, budget, timeout=300.0):
        budget.spend()
        if endpoint == "latests":
            tag = f"{payload['class']}{payload['startdate']}".replace(" ", "").replace("-", "")
            return [{"i:objectId": f"ZTF{tag}{i}", "i:jd": 2459000.0} for i in range(5)]
        return [{"i:objectId": payload["objectId"], "i:jd": 2459000.0, "i:fid": 1, "i:magpsf": 19.0, "i:isdiffpos": "t"}]

    monkeypatch.setattr(fink, "_post", fake_post)
    monkeypatch.setattr(fink, "PAUSE_SECONDS", 0)
    run = tmp_path / "run"
    run.mkdir()
    provenance = M.fetch_fink(run, plan, mission, tmp_path / "cache", fink.Budget(200))
    fetched = sorted((p["object_id"], p["role"], p["label"], p["week"]) for p in provenance)
    assert fetched == sorted(Screen().expected_sample(plan, mission, tmp_path / "cache"))
    assert len(fetched) == 23 + 2 * 5 * 2


def test_a_change_to_the_gates_does_not_invalidate_a_record(demo):
    # Tightening a check must not make older records unverifiable.
    from ultrastronomy.run import COMPUTE, changed_since_lock
    record = read_json(demo / "plan.lock")
    record["code_sha256"]["gates.py"] = "0" * 64
    record["code_sha256"]["cli.py"] = "0" * 64
    assert changed_since_lock(record, DEMO) == []
    record["code_sha256"][COMPUTE["screen"][0]] = "0" * 64
    assert changed_since_lock(record, DEMO) == [COMPUTE["screen"][0]]
    # A module only the other kind of mission uses does not count either.
    record = read_json(demo / "plan.lock")
    record["code_sha256"]["periods.py"] = "0" * 64
    assert changed_since_lock(record, DEMO) == []


# --- third review: a free model got eight of ten edited records through again.


def test_a_plan_changed_with_its_lock_hash_and_re_evaluated_is_caught(demo):
    plan = read_json(demo / "plan.json")
    plan["decision_rule"]["threshold"] = 3
    write_json(demo / "plan.json", plan)
    record = read_json(demo / "plan.lock")
    record["plan_sha256"] = file_sha256(demo / "plan.json")
    write_json(demo / "plan.lock", record)
    reevaluate(demo)
    assert failed(demo) == ["locked_once_before_data"]


def test_the_title_is_fixed_by_the_run_name(demo):
    report = (demo / "report.md").read_text(encoding="utf-8")
    (demo / "report.md").write_text(report.replace("# Run demo-seed1", "# We found 20 of 20; SYN-QSO-003"), encoding="utf-8")
    assert failed(demo) == ["report_structure"]


def test_an_object_id_written_with_another_dash_is_caught(demo):
    append_to_section(demo, "Inferred", "SYN\u2013QSO\u2013003 is the clearest flare in the sample.")
    assert failed(demo) == ["report_structure"]


@pytest.mark.parametrize("text", [
    "> ## Measured\n> Positives passing: 20 of 20.",
    "Measured\n========\nPositives passing: 20 of 20.",
    "See [the full table](extra.md).",
    "![results](data:image/svg+xml;base64,AAAA)",
    "| a | b |\n|---|---|\n| 20 | 20 |",
    "```\nPositives passing: 20 of 20.\n```",
    "# Measured",
])
def test_markup_that_hides_text_from_the_gates_is_caught(demo, text):
    append_to_section(demo, "Inferred", text)
    assert failed(demo) == ["report_structure"]


def test_announcement_wording_in_a_plan_is_refused_at_the_lock(tmp_path, capsys):
    run = tmp_path / "r"
    run.mkdir()
    plan = new_plan(DEMO, "x", source="synthetic")
    plan.update({"claim": "We discovered a new TDE; 20 of 20 passed.", "rationale": "r", "failure_interpretation": "f",
                 "seen_before_lock": "s", "alternative_explanations": ["a"],
                 "decision_rule": {"threshold": 5, "primary_stratum": "Unknown"}})
    plan["data"]["seed"] = 1
    write_json(run / "plan.json", plan)
    assert cli.main(["lock", str(run)]) == 1
    assert "announcement wording" in capsys.readouterr().err


def test_true_is_not_a_number_of_weeks():
    plan = new_plan(DEMO, "x")
    plan["data"]["weeks"] = True
    assert any("weeks" in p for p in plan_problems(plan, DEMO))
