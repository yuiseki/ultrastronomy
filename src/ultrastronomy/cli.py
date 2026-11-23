"""`ultra`: the command-line entry point of the harness."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from . import mission as M
from .gates import run_gates
from .intervals import wilson
from .run import lock, log, new_plan, plan_problems, read_json, require_lock, write_json

SHARED = ["plan.json", "plan.lock", "provenance.json", "results.json", "claims.json", "report.md"]


def cache_dir() -> Path:
    return Path(os.environ.get("ULTRA_CACHE", ".cache/fink"))


def _pct(k, n):
    return f"{k}/{n}" + (f" ({100 * k / n:.0f}%)" if n else "")


def print_results(results: dict) -> None:
    d = results["decision"]
    strata = sorted(results["recall_vs_load"][0]["background"])
    print(f"data source: {results['data_source']}")
    print("\nscore >=  known objects   " + "   ".join(strata))
    for row in results["recall_vs_load"]:
        cells = "   ".join(_pct(row["background"][s]["passed"], row["background"][s]["n"]).ljust(len(s)) for s in strata)
        print(f"   {row['threshold']}      {_pct(row['truth_kept'], row['truth_n']).ljust(14)}  {cells}")
    print(f"\nlocked rule: score >= {d['threshold']}, positives against the '{d['primary_stratum']}' stratum")
    print(f"  positives passing: {_pct(d['positives_passed'], d['positives_n'])}")
    print(f"  background passing: {_pct(d['background_passed'], d['background_n'])}")
    if d["difference"] is not None:
        print(f"  difference {d['difference']:+.3f}, 95% interval {d['ci95_low']:+.3f} to {d['ci95_high']:+.3f}")
    print(f"  verdict: {d['verdict']}")
    if results.get("injection"):
        print("\ninjected TDE-like flares recovered, by peak magnitude (" + results["injection"]["cadence_model"] + "):")
        print("  " + "  ".join(f"{b['peak_mag']:.1f}: {100 * b['recovery']:.0f}%" for b in results["injection"]["bins"]))


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
    mission = M.load_mission(read_json(run / "plan.json")["mission"])
    try:
        record = lock(run, mission)
    except ValueError as e:
        log(run, "lock_refused", reason=str(e))
        print(e, file=sys.stderr)
        return 1
    print(f"locked at {record['locked_at']}. The plan and the scoring code are now fixed for this run.")
    return 0


def cmd_fetch(a) -> int:
    run = Path(a.run)
    try:
        require_lock(run)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    plan = read_json(run / "plan.json")
    mission = M.load_mission(plan["mission"])
    if plan["data"]["source"] == "synthetic":
        provenance, _ = M.fetch_synthetic(plan)
        write_json(run / "provenance.json", provenance)
        return 0
    planned = M.planned_requests(plan, mission)
    print(f"this plan needs at most {planned} requests to the Fink API (about {planned * 4 // 60 + 1} minutes); "
          f"the budget in plan.json is {plan['data']['max_requests']}. Cached objects cost nothing.")
    if not a.confirm:
        print("nothing was fetched. Re-run with --confirm to go ahead.")
        return 0
    try:
        provenance = M.fetch_fink(run, plan, mission, cache_dir())
    except Exception as e:  # network errors and the budget: record, never paper over
        log(run, "fetch_failed", error=f"{type(e).__name__}: {e}")
        print(f"fetch failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    write_json(run / "provenance.json", provenance)
    print(f"fetched {len(provenance)} objects. Next: `ultra evaluate {run}`.")
    return 0


def cmd_evaluate(a) -> int:
    run = Path(a.run)
    try:
        require_lock(run)
        plan = read_json(run / "plan.json")
        mission = M.load_mission(plan["mission"])
        provenance = read_json(run / "provenance.json")
        objects = M.load_objects(plan, provenance, cache_dir())
    except (ValueError, FileNotFoundError) as e:
        log(run, "evaluate_failed", error=str(e))
        print(e, file=sys.stderr)
        return 1
    results = M.evaluate(objects, provenance, plan, mission)
    if (run / "results.json").exists():  # keep an injection that was already run
        results["injection"] = read_json(run / "results.json").get("injection")
    write_json(run / "results.json", results)
    log(run, "evaluate", verdict=results["decision"]["verdict"])
    print_results(results)
    return 0


def cmd_inject(a) -> int:
    run = Path(a.run)
    try:
        require_lock(run)
        results = read_json(run / "results.json")
    except (ValueError, FileNotFoundError) as e:
        print(e, file=sys.stderr)
        return 1
    plan = read_json(run / "plan.json")
    results["injection"] = M.injection(plan["data"]["seed"], plan["decision_rule"]["threshold"])
    write_json(run / "results.json", results)
    log(run, "inject")
    print_results(results)
    return 0


def cmd_gates(a) -> int:
    run = Path(a.run)
    mission = M.load_mission(read_json(run / "plan.json")["mission"])
    gates = run_gates(run, mission, cache_dir())
    log(run, "gates", failed=[g["gate"] for g in gates if not g["passed"]])
    for g in gates:
        print(("PASS  " if g["passed"] else "FAIL  ") + g["gate"] + ("" if g["passed"] else f": {g['detail']}"))
    return 0 if all(g["passed"] for g in gates) else 1


def cmd_status(a) -> int:
    run = Path(a.run)
    steps = [
        ("plan.json", "write the plan", f"edit {run}/plan.json"),
        ("plan.lock", "lock the plan", f"ultra lock {run}"),
        ("provenance.json", "fetch the data", f"ultra fetch {run} --confirm"),
        ("results.json", "score and decide", f"ultra evaluate {run}"),
    ]
    for name, label, command in steps:
        if not (run / name).exists():
            print(f"next: {label}  ->  {command}")
            return 0
        print(f"done: {label}")
    results = read_json(run / "results.json")
    if not results.get("injection"):
        print(f"next: measure sensitivity  ->  ultra inject {run}")
        return 0
    print("done: measure sensitivity")
    for name in ("claims.json", "report.md"):
        if not (run / name).exists():
            print(f"next: write {run}/{name} (see the ultra-report skill)")
            return 0
    print(f"next: check the record  ->  ultra gates {run}")
    return 0


def cmd_export(a) -> int:
    run = Path(a.run)
    plan = read_json(run / "plan.json")
    mission = M.load_mission(plan["mission"])
    failed = [g["gate"] for g in run_gates(run, mission, cache_dir()) if not g["passed"]]
    if failed:
        print(f"not exported: gates failed: {failed}", file=sys.stderr)
        return 1
    if plan["data"]["source"] != "fink":
        print("not exported: a synthetic run is a demo, not a contribution", file=sys.stderr)
        return 1
    dest = Path(a.contributions_dir) / run.name
    if dest.exists():
        print(f"{dest} already exists", file=sys.stderr)
        return 1
    dest.mkdir(parents=True)
    for name in SHARED:
        shutil.copy(run / name, dest / name)
    print(f"copied the record to {dest}. Commit it and open a pull request.")
    return 0


def pool(contributions: Path) -> dict:
    """Pass rates over every contributed run, each background object counted once."""
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
    result = pool(Path(a.contributions_dir))
    print(json.dumps(result, indent=2))
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
        "alternative_explanations": ["The synthetic classes were written by the same people as the screen."],
        "seen_before_lock": "Nothing: the data is generated after the lock.",
    })
    plan["data"]["seed"] = a.seed
    write_json(run / "plan.json", plan)
    assert not plan_problems(plan, mission)
    lock(run, mission)
    provenance, objects = M.fetch_synthetic(plan)
    write_json(run / "provenance.json", provenance)
    results = M.evaluate(objects, provenance, plan, mission)
    results["injection"] = M.injection(a.seed, 5)
    write_json(run / "results.json", results)
    d = results["decision"]
    write_json(run / "claims.json", [
        {"kind": "measured", "text": "Verdict of the locked rule.", "evidence": "/decision/verdict", "value": d["verdict"]},
        {"kind": "measured", "text": "Synthetic flares scoring 5 or more.", "evidence": "/decision/positives_passed", "value": d["positives_passed"]},
        {"kind": "unverified", "text": "Whether any of this holds on the real sky.", "basis": "The demo never touches real data."},
    ])
    (run / "report.md").write_text(
        "# Demo run on synthetic data\n\n## Measured\n\n"
        f"- Verdict of the locked rule: {d['verdict']}.\n"
        f"- {d['positives_passed']} of {d['positives_n']} synthetic flares score 5 or more, against "
        f"{d['background_passed']} of {d['background_n']} objects in the Unknown stratum.\n\n"
        "## Inferred\n\nNothing.\n\n## Not verified\n\n"
        "- Everything about the real sky. Every light curve here comes from a formula.\n", encoding="utf-8")
    print("ultrastronomy demo: every light curve below is synthetic.\n")
    print_results(results)
    gates = run_gates(run, mission)
    print("\ngates: " + ", ".join(("ok " if g["passed"] else "FAILED ") + g["gate"] for g in gates))
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
        ("lock", cmd_lock, "freeze the plan and the scoring code"),
        ("evaluate", cmd_evaluate, "score every object and apply the locked rule"),
        ("inject", cmd_inject, "measure sensitivity with injected synthetic flares"),
        ("gates", cmd_gates, "check the record; exit 1 if any gate fails"),
        ("status", cmd_status, "show what is done and what comes next"),
    ]:
        s = sub.add_parser(name, help=text)
        s.add_argument("run")
        s.set_defaults(fn=fn)

    s = sub.add_parser("fetch", help="download the data the locked plan asks for")
    s.add_argument("run")
    s.add_argument("--confirm", action="store_true", help="without this, only the request count is shown")
    s.set_defaults(fn=cmd_fetch)

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
