"""`ultra`: the command-line entry point of the harness."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from . import fink
from . import mission as M
from .gates import run_gates
from .intervals import wilson
from .run import lock, log, new_plan, plan_problems, read_json, require_lock, write_json

SHARED = ["plan.json", "plan.lock", "log.jsonl", "provenance.json", "results.json", "measured.md",
          "claims.json", "report.md"]


def cache_dir() -> Path:
    return Path(os.environ.get("ULTRA_CACHE", ".cache/fink"))


def _mission_of(run: Path) -> dict:
    return M.load_mission(read_json(run / "plan.json")["mission"])


def _pct(k, n):
    return f"{k}/{n}" + (f" ({100 * k / n:.0f}%)" if n else "")


def print_results(results: dict) -> None:
    strata = sorted(results["recall_vs_load"][0]["background"])
    print("score >=  positives      all known      " + "   ".join(strata))
    for row in results["recall_vs_load"]:
        cells = "   ".join(_pct(row["background"][s]["passed"], row["background"][s]["n"]).ljust(len(s)) for s in strata)
        print(f"   {row['threshold']}      {_pct(row['positives_kept'], row['positives_n']).ljust(14)} "
              f"{_pct(row['truth_kept'], row['truth_n']).ljust(14)} {cells}")
    print("\n'positives' are the known objects the rule is about; 'all known' adds the supernova candidates.\n")
    print(M.measured_markdown(results))


def cmd_init(a) -> int:
    run = Path(a.runs_dir) / a.name
    if run.exists():
        print(f"{run} already exists", file=sys.stderr)
        return 1
    mission = M.load_mission(a.mission)
    run.mkdir(parents=True)
    write_json(run / "plan.json", new_plan(mission, a.ai_budget))
    log(run, "init", mission=a.mission)
    print(f"created {run}/plan.json. Fill it in, then run `ultra lock {run}`.")
    return 0


def cmd_lock(a) -> int:
    run = Path(a.run)
    mission = _mission_of(run)
    plan = read_json(run / "plan.json")
    try:
        if not plan_problems(plan, mission) and plan["data"]["source"] == "fink":
            needed = M.planned_requests(plan, mission)
            if needed > plan["data"]["max_requests"]:
                raise ValueError(f"this plan can need {needed} requests but `data.max_requests` is "
                                 f"{plan['data']['max_requests']}. Raise the budget or sample less.")
        record = lock(run, mission)
    except ValueError as e:
        log(run, "lock_refused", reason=str(e))
        print(e, file=sys.stderr)
        return 1
    print(f"locked at {record['locked_at']}. The plan, the code and the mission files are now fixed for this run.")
    return 0


def cmd_fetch(a) -> int:
    run = Path(a.run)
    mission = _mission_of(run)
    try:
        require_lock(run, mission)
    except ValueError as e:
        log(run, "fetch_refused", reason=str(e))
        print(e, file=sys.stderr)
        return 1
    plan = read_json(run / "plan.json")
    if plan["data"]["source"] == "synthetic":
        write_json(run / "provenance.json", M.fetch_synthetic(plan)[0])
        log(run, "fetch", requests_used=0)
        return 0
    planned, spent = M.planned_requests(plan, mission), M.requests_spent(run)
    left = plan["data"]["max_requests"] - spent
    print(f"this plan needs at most {planned} requests to the Fink API (about {planned * 4 // 60 + 1} minutes). "
          f"Budget: {plan['data']['max_requests']}, already used by this run: {spent}. Cached objects cost nothing.")
    if not a.confirm:
        print("nothing was fetched. Re-run with --confirm to go ahead.")
        return 0
    budget = fink.Budget(max(left, 0))
    try:
        provenance = M.fetch_fink(run, plan, mission, cache_dir(), budget)
    except Exception as e:  # network errors and the budget: record, never paper over
        log(run, "fetch_failed", error=f"{type(e).__name__}: {e}", requests_used=budget.used)
        print(f"fetch failed after {budget.used} requests: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    write_json(run / "provenance.json", provenance)
    log(run, "fetch", requests_used=budget.used, objects=len(provenance))
    got = Counter(p["label"] for p in provenance if p["role"] == "background")
    want = plan["data"]["weeks"] * plan["data"]["per_class"]
    print(f"fetched {len(provenance)} objects with {budget.used} requests. Background objects per stratum (asked for {want}):")
    for stratum in mission["strata"]:
        note = "" if got[stratum] == want else "   <- fewer than asked: some weeks returned nothing for this class"
        print(f"  {stratum}: {got[stratum]}{note}")
    print("An empty week is usually a week without observations, or a class label Fink no longer uses. "
          f"The weeks are in {run}/log.jsonl.\nNext: `ultra evaluate {run}`.")
    return 0


def cmd_evaluate(a) -> int:
    run = Path(a.run)
    try:
        mission = _mission_of(run)
        require_lock(run, mission)
        plan = read_json(run / "plan.json")
        provenance = read_json(run / "provenance.json")
        objects = M.load_objects(plan, provenance, cache_dir())
    except (ValueError, FileNotFoundError) as e:
        log(run, "evaluate_failed", error=str(e))
        print(e, file=sys.stderr)
        return 1
    results = M.compute(objects, provenance, plan, mission, with_injection=True)
    write_json(run / "results.json", results)
    (run / "measured.md").write_text(M.measured_markdown(results), encoding="utf-8")
    log(run, "evaluate", verdict=results["decision"]["verdict"])
    print_results(results)
    print(f"The sentences above are in {run}/measured.md. Next: write claims.json and report.md.")
    return 0


def _print_gates(gates) -> int:
    for g in gates:
        print(("PASS  " if g["passed"] else "FAIL  ") + g["gate"] + ("" if g["passed"] else f": {g['detail']}"))
    return 0 if all(g["passed"] for g in gates) else 1


def cmd_gates(a) -> int:
    run = Path(a.run)
    gates = run_gates(run, _mission_of(run), cache_dir())
    log(run, "gates", failed=[g["gate"] for g in gates if not g["passed"]])
    return _print_gates(gates)


def cmd_verify(a) -> int:
    """Check someone else's record, with data fetched again by this machine."""
    record = Path(a.record)
    mission = _mission_of(record)
    cache = cache_dir()
    if a.refetch:
        provenance = read_json(record / "provenance.json")
        cache = Path(".cache/verify") / record.name
        print(f"re-fetching {len(provenance)} objects into {cache} (at most {len(provenance)} requests).")
        if not a.confirm:
            print("nothing was fetched. Re-run with --confirm to go ahead.")
            return 0
        budget = fink.Budget(len(provenance))
        for p in provenance:
            fink.object_alerts(p["object_id"], cache, budget, mission["alerts_until"])
    return _print_gates(run_gates(record, mission, cache))


def cmd_status(a) -> int:
    run = Path(a.run)
    if not (run / "plan.json").exists():
        print(f"next: start a run  ->  ultra init {run.name} --ai-budget \"...\"")
        return 0
    mission = _mission_of(run)
    plan = read_json(run / "plan.json")
    if not (run / "plan.lock").exists():
        problems = plan_problems(plan, mission)
        if problems:
            print(f"next: fill in {run}/plan.json (see the ultra-plan skill). Still to do:")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"done: write the plan\nnext: lock it  ->  ultra lock {run}")
        return 0
    print("done: write and lock the plan")
    if not (run / "provenance.json").exists():
        print(f"next: fetch the data  ->  ultra fetch {run}   (shows the request count; add --confirm to go ahead)")
        return 0
    print("done: fetch the data")
    if not (run / "results.json").exists():
        print(f"next: score and decide  ->  ultra evaluate {run}")
        return 0
    print("done: score, decide and measure sensitivity")
    missing = [n for n in ("claims.json", "report.md") if not (run / n).exists()]
    if missing:
        print(f"next: write {' and '.join(missing)} in {run}/ (see the ultra-report skill)")
        return 0
    failed = [g["gate"] for g in run_gates(run, mission, cache_dir()) if not g["passed"]]
    if failed:
        print(f"next: fix what the gates name  ->  ultra gates {run}   (failing: {', '.join(failed)})")
        return 0
    print("done: the record passes every gate")
    exported = Path(a.contributions_dir) / run.name
    if plan["data"]["source"] != "fink":
        print("this is a synthetic run: a demo, not a contribution. Nothing more to do.")
    elif not exported.exists():
        print(f"next: copy the record for sharing  ->  ultra export {run}")
    else:
        print(f"done: exported to {exported}. Sharing it (commit, pull request) is the person's decision.")
    return 0


def cmd_export(a) -> int:
    run = Path(a.run)
    plan = read_json(run / "plan.json")
    if plan["data"]["source"] != "fink":
        print("not exported: a synthetic run is a demo, not a contribution", file=sys.stderr)
        return 1
    failed = [g["gate"] for g in run_gates(run, _mission_of(run), cache_dir()) if not g["passed"]]
    if failed:
        print(f"not exported: gates failed: {failed}", file=sys.stderr)
        return 1
    dest = Path(a.contributions_dir) / run.name
    if dest.exists():
        print(f"{dest} already exists", file=sys.stderr)
        return 1
    dest.mkdir(parents=True)
    for name in SHARED:
        shutil.copy(run / name, dest / name)
    log(run, "export", to=str(dest))
    print(f"copied the record to {dest}. It holds no raw data. Ask the person before committing or opening a pull request.")
    return 0


def pool(contributions: Path) -> dict:
    """Pass rates over every contributed run, each background object counted once.

    Pooling trusts the records it is given. Records enter `contributions/`
    through review, where `ultra verify --refetch` recomputes them.
    """
    seen, runs, rows = set(), 0, []
    for results_path in sorted(contributions.glob("*/results.json")):
        results = read_json(results_path)
        if results["data_source"] != "fink":
            continue
        runs += 1
        for o in results["objects"]:
            if o["role"] == "background" and o["id"] not in seen:
                seen.add(o["id"])
                rows.append(o)
    strata = sorted({o["label"] for o in rows})
    table = []
    for threshold in range(6, 0, -1):
        cells = {}
        for s in strata:
            scores = [o["score"] for o in rows if o["label"] == s]
            k = sum(x >= threshold for x in scores)
            lo, hi = wilson(k, len(scores))
            cells[s] = {"passed": k, "n": len(scores), "ci95_low": lo, "ci95_high": hi}
        table.append({"threshold": threshold, "background": cells})
    return {"runs": runs, "background_objects": len(rows), "table": table}


def cmd_pool(a) -> int:
    print(json.dumps(pool(Path(a.contributions_dir)), indent=2))
    return 0


def cmd_demo(a) -> int:
    """The whole pipeline on synthetic data: no network, nothing to install beyond this package."""
    run = Path(a.runs_dir) / f"demo-seed{a.seed}"
    if run.exists():
        shutil.rmtree(run)
    run.mkdir(parents=True)
    mission = M.load_mission("demo")
    plan = new_plan(mission, "none: the demo uses no AI", source="synthetic")
    plan.update({
        "claim": "Synthetic TDE-like flares pass the screen more often than synthetic variable stars and artefacts.",
        "decision_rule": {"threshold": 5, "primary_stratum": "Unknown"},
        "rationale": "Demo values. In a real run you choose these before looking at data and say why.",
        "failure_interpretation": "The screen does not separate even idealised flares; fix the pipeline before using real data.",
        "alternative_explanations": ["The synthetic classes were written by the same people as the screen, "
                                     "and the Unknown class is built from objects the criteria exclude almost by construction."],
        "seen_before_lock": "Nothing: the data is generated after the lock.",
    })
    plan["data"]["seed"] = a.seed
    write_json(run / "plan.json", plan)
    log(run, "init", mission="demo")
    lock(run, mission)
    provenance, objects = M.fetch_synthetic(plan)
    write_json(run / "provenance.json", provenance)
    log(run, "fetch", requests_used=0)
    results = M.compute(objects, provenance, plan, mission, with_injection=True)
    write_json(run / "results.json", results)
    measured = M.measured_markdown(results)
    (run / "measured.md").write_text(measured, encoding="utf-8")
    log(run, "evaluate", verdict=results["decision"]["verdict"])
    write_json(run / "claims.json", [
        {"kind": "inferred", "text": "The pipeline runs end to end and separates idealised classes.",
         "basis": "The verdict and table in measured.md. The classes are synthetic, so this says nothing about the sky."},
        {"kind": "unverified", "text": "Whether any of this holds on real data.",
         "basis": "The demo never touches real data."},
    ])
    (run / "report.md").write_text(
        "# Demo run on synthetic data\n\n## Measured\n\n" + measured +
        "\n## Inferred\n\nThe pipeline runs end to end and separates idealised classes. That is all a demo can show.\n\n"
        "## Not verified\n\n- Everything about the real sky. Every light curve here comes from a formula.\n", encoding="utf-8")
    print("ultrastronomy demo: every light curve below is synthetic.\n")
    print_results(results)
    gates = run_gates(run, mission)
    print("gates: " + ", ".join(("ok " if g["passed"] else "FAILED ") + g["gate"] for g in gates))
    print(f"\nThe full record is in {run}/. A real run follows the same steps on ZTF alerts: see AGENTS.md.")
    return 0 if all(g["passed"] for g in gates) else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ultra", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("demo", help="run the whole pipeline on synthetic data, offline")
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--runs-dir", default="runs")
    s.set_defaults(fn=cmd_demo)

    s = sub.add_parser("init", help="start a run: writes an empty plan")
    s.add_argument("name")
    s.add_argument("--mission", default="ztf-nuclear-transients")
    s.add_argument("--ai-budget", required=True,
                   help="the limit the human set for this run, in their words (e.g. '30 minutes, stop after the first table')")
    s.add_argument("--runs-dir", default="runs")
    s.set_defaults(fn=cmd_init)

    for name, fn, text in [
        ("lock", cmd_lock, "freeze the plan, the code and the mission files"),
        ("evaluate", cmd_evaluate, "score every object, apply the locked rule, measure sensitivity"),
        ("gates", cmd_gates, "recompute and check the record; exit 1 if any gate fails"),
    ]:
        s = sub.add_parser(name, help=text)
        s.add_argument("run")
        s.set_defaults(fn=fn)

    s = sub.add_parser("status", help="show what is done and what comes next")
    s.add_argument("run")
    s.add_argument("--contributions-dir", default="contributions")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("fetch", help="download the data the locked plan asks for")
    s.add_argument("run")
    s.add_argument("--confirm", action="store_true", help="without this, only the request count is shown")
    s.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("verify", help="check a shared record, optionally with data fetched again")
    s.add_argument("record")
    s.add_argument("--refetch", action="store_true", help="download the record's objects again and compare")
    s.add_argument("--confirm", action="store_true", help="without this, only the request count is shown")
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("export", help="copy a run that passed the gates into contributions/")
    s.add_argument("run")
    s.add_argument("--contributions-dir", default="contributions")
    s.set_defaults(fn=cmd_export)

    s = sub.add_parser("pool", help="pool the background pass rates of all contributed runs")
    s.add_argument("--contributions-dir", default="contributions")
    s.set_defaults(fn=cmd_pool)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
