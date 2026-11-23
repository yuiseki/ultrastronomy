"""The rediscovery mission: sample, fetch, score, decide, inject."""

from __future__ import annotations

import csv
import datetime as dt
import random
from collections import Counter, defaultdict
from pathlib import Path

from . import fink, synth
from .intervals import newcombe_difference, wilson
from .lightcurve import light_curve_features
from .run import log, read_json, write_json
from .score import CRITERIA, met, tde_likeness

ROOT = Path(__file__).resolve().parents[2]


def load_mission(mission_id: str, missions_dir: Path | None = None) -> dict:
    folder = (missions_dir or ROOT / "missions") / mission_id
    mission = read_json(folder / "mission.json")
    mission["dir"] = folder
    with (folder / mission["ground_truth"]).open(newline="", encoding="utf-8") as fh:
        mission["truth"] = list(csv.DictReader(fh, delimiter="\t"))
    return mission


def sample_weeks(seed: int, n: int, first: str, last: str) -> list[str]:
    rng = random.Random(seed)
    a, b = dt.date.fromisoformat(first), dt.date.fromisoformat(last)
    span = (b - a).days - 7
    return sorted((a + dt.timedelta(days=rng.randrange(span))).isoformat() for _ in range(n))


def planned_requests(plan: dict, mission: dict) -> int:
    """Upper bound on network requests for this plan, with an empty cache."""
    d = plan["data"]
    cells = d["weeks"] * len(mission["strata"])
    return len(mission["truth"]) + cells + cells * d["per_class"]


def requests_spent(run: Path) -> int:
    """Network requests this run has already made, over every earlier attempt."""
    spent = 0
    if (run / "log.jsonl").exists():
        for line in (run / "log.jsonl").read_text(encoding="utf-8").splitlines():
            spent += __import__("json").loads(line).get("requests_used", 0)
    return spent


def fetch_fink(run: Path, plan: dict, mission: dict, cache: Path, budget: fink.Budget) -> list[dict]:
    """Fetch truth and a background sample. Returns the provenance records."""
    d = plan["data"]
    rng = random.Random(d["seed"])
    truth_ids = {t["ztf_id"] for t in mission["truth"]}
    todo = [(t["ztf_id"], "truth", t["group"], "") for t in mission["truth"]]
    for week in sample_weeks(d["seed"], d["weeks"], mission["first_date"], mission["last_date"]):
        stop = (dt.date.fromisoformat(week) + dt.timedelta(days=7)).isoformat()
        for stratum in mission["strata"]:
            entry = fink.class_week(stratum, week, stop, cache, budget)
            taken = {oid for oid, *_ in todo}
            ids = [i for i in entry["ids"] if i not in truth_ids and i not in taken]
            picked = rng.sample(ids, min(d["per_class"], len(ids)))
            log(run, "sample", week=week, stratum=stratum, available=len(ids), picked=picked)
            todo += [(oid, "background", stratum, week) for oid in picked]
    provenance = []
    for oid, role, label, week in todo:
        entry = fink.object_alerts(oid, cache, budget, mission["alerts_until"])
        provenance.append({
            "object_id": oid, "role": role, "label": label, "week": week,
            "source": entry["source"], "retrieved_at": entry["retrieved_at"],
            "accessed_at": fink.now(), "sha256": fink.sha256_rows(entry["rows"]), "n_alerts": len(entry["rows"]),
        })
    return provenance


def fetch_synthetic(plan: dict) -> tuple[list[dict], dict]:
    objects, truth, background = synth.demo_population(plan["data"]["seed"])
    stamp = fink.now()
    labels = [(t["ztf_id"], "truth", t["group"]) for t in truth] + [(b["ztf_id"], "background", b["stratum"]) for b in background]
    provenance = [{
        "object_id": oid, "role": role, "label": label, "week": "", "source": "synthetic",
        "retrieved_at": stamp, "accessed_at": stamp, "sha256": fink.sha256_rows(objects[oid]),
        "n_alerts": len(objects[oid]),
    } for oid, role, label in labels]
    return provenance, objects


def load_objects(plan: dict, provenance: list[dict], cache: Path) -> dict:
    """Rows of every object in the provenance, refusing content that changed."""
    if plan["data"]["source"] == "synthetic":
        objects = synth.demo_population(plan["data"]["seed"])[0]
    else:
        objects = {p["object_id"]: read_json(cache / "objects" / f"{p['object_id']}.json")["rows"] for p in provenance}
    for p in provenance:
        if fink.sha256_rows(objects[p["object_id"]]) != p["sha256"]:
            raise ValueError(f"{p['object_id']}: data no longer matches the hash in provenance.json")
    return objects


# Below this many objects on either side the rule gives no verdict. The score
# interval used here is known to hold its coverage from roughly ten objects up;
# with two or three it can exclude zero on almost no evidence.
MIN_OBJECTS = 10


def decide(k_pos: int, n_pos: int, k_bg: int, n_bg: int) -> dict:
    """Apply the fixed rule to a difference of pass rates, positives minus background.

    supported: the 95% interval lies above zero. rejected: it lies below zero.
    undecided: it contains zero, or either side has fewer than MIN_OBJECTS.
    "No difference seen" is undecided, not rejected.
    """
    out = {"positives_passed": k_pos, "positives_n": n_pos, "background_passed": k_bg, "background_n": n_bg}
    if n_pos < MIN_OBJECTS or n_bg < MIN_OBJECTS:
        d = (k_pos / n_pos - k_bg / n_bg) if n_pos and n_bg else None
        return {**out, "difference": d, "ci95_low": None, "ci95_high": None, "verdict": "undecided",
                "reason": f"fewer than {MIN_OBJECTS} objects on one side of the comparison"}
    d, lo, hi = newcombe_difference(k_pos, n_pos, k_bg, n_bg)
    verdict = "supported" if lo > 0 else "rejected" if hi < 0 else "undecided"
    return {**out, "difference": d, "ci95_low": lo, "ci95_high": hi, "verdict": verdict, "reason": ""}


def evaluate(objects: dict, provenance: list[dict], plan: dict, mission: dict) -> dict:
    """Score every object and apply the locked decision rule. Pure function."""
    scored = []
    for p in sorted(provenance, key=lambda p: p["object_id"]):
        f = light_curve_features(objects[p["object_id"]])
        scored.append({
            "id": p["object_id"], "role": p["role"], "label": p["label"],
            "score": tde_likeness(f) if f else 0, "met": met(f) if f else {},
            "no_positive_detection": f is None, "n_det": f["n_det"] if f else 0,
        })
    truth = [s for s in scored if s["role"] == "truth"]
    background = [s for s in scored if s["role"] == "background"]
    positives = [s for s in truth if s["label"] in mission["positive_groups"]]
    strata = defaultdict(list)
    for s in background:
        strata[s["label"]].append(s)

    table = []
    for threshold in range(len(CRITERIA), 0, -1):
        table.append({
            "threshold": threshold,
            "truth_kept": sum(s["score"] >= threshold for s in truth), "truth_n": len(truth),
            "positives_kept": sum(s["score"] >= threshold for s in positives), "positives_n": len(positives),
            "background": {name: {"passed": sum(s["score"] >= threshold for s in rows), "n": len(rows)}
                           for name, rows in sorted(strata.items())},
        })
    rule = plan["decision_rule"]
    primary = strata.get(rule["primary_stratum"], [])
    decision = {"threshold": rule["threshold"], "primary_stratum": rule["primary_stratum"], **decide(
        sum(s["score"] >= rule["threshold"] for s in positives), len(positives),
        sum(s["score"] >= rule["threshold"] for s in primary), len(primary))}
    return {
        "data_source": plan["data"]["source"],
        "columns_used": sorted({"i:jd", "i:fid", "i:magpsf", "i:isdiffpos", "i:distpsnr1", "i:sgscore1"}),
        "objects": scored,
        "criteria_met": {name: {
            "truth": sum(s["met"].get(name, False) for s in truth), "truth_n": len(truth),
            "background": sum(s["met"].get(name, False) for s in background), "background_n": len(background),
        } for name in CRITERIA},
        "no_positive_detection": dict(Counter(s["label"] for s in background if s["no_positive_detection"])),
        "recall_vs_load": table,
        "decision": decision,
    }


INJECTION_BINS = [17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5]


INJECTIONS_PER_BIN = 100


def injection(seed: int, threshold: int, n_per_bin: int = INJECTIONS_PER_BIN) -> dict:
    """Recovery of synthetic TDE-like flares against peak magnitude.

    Hosts are injected as nuclear and non-stellar, so this measures what the
    photometric criteria lose to faintness and sampling. It does not measure
    host confusion, and the cadence is a model, not ZTF's schedule.
    """
    rng = random.Random(seed)
    bins = []
    for peak in INJECTION_BINS:
        recovered = 0
        for _ in range(n_per_bin):
            rows = synth.tde_like(rng, synth.cadence(rng, 2459000.0, 900), peak)
            f = light_curve_features(rows)
            recovered += bool(f and tde_likeness(f) >= threshold)
        lo, hi = wilson(recovered, n_per_bin)
        bins.append({"peak_mag": peak, "n": n_per_bin, "recovered": recovered,
                     "recovery": recovered / n_per_bin, "ci95_low": lo, "ci95_high": hi})
    return {"seed": seed, "threshold": threshold, "cadence_model": synth.CADENCE_MODEL,
            "host": "injected as nuclear (0.2 arcsec) in a non-stellar host", "bins": bins}


def compute(objects: dict, provenance: list[dict], plan: dict, mission: dict, with_injection: bool) -> dict:
    """Everything results.json holds, from data and plan alone. The gates call this again."""
    results = evaluate(objects, provenance, plan, mission)
    results["injection"] = injection(plan["data"]["seed"], plan["decision_rule"]["threshold"]) if with_injection else None
    return results


def _share(k: int, n: int) -> str:
    return f"{k} of {n}"


def measured_markdown(results: dict) -> str:
    """The results as sentences. report.md must carry this text unchanged under '## Measured'."""
    d = results["decision"]
    row = next(r for r in results["recall_vs_load"] if r["threshold"] == d["threshold"])
    synthetic = results["data_source"] == "synthetic"
    lines = [
        f"- Data: {'synthetic light curves, generated by formula' if synthetic else 'ZTF alert photometry from the Fink API'}.",
        f"- Locked rule: score of {d['threshold']} or more; positives against the `{d['primary_stratum']}` stratum.",
        f"- Positives passing: {_share(d['positives_passed'], d['positives_n'])}. "
        f"`{d['primary_stratum']}` objects passing: {_share(d['background_passed'], d['background_n'])}.",
    ]
    if d["ci95_low"] is None:
        lines.append(f"- Verdict: {d['verdict']} ({d['reason']}). No interval was computed.")
    else:
        lines.append(f"- Difference in pass rates: {d['difference']:+.3f}, 95% interval {d['ci95_low']:+.3f} to {d['ci95_high']:+.3f}.")
        lines.append(f"- Verdict: {d['verdict']}.")
    lines.append(f"- All known objects passing at that score, supernova candidates included: {_share(row['truth_kept'], row['truth_n'])}.")
    for name, cell in row["background"].items():
        lines.append(f"- `{name}` objects passing at that score: {_share(cell['passed'], cell['n'])}.")
    none = sum(results["no_positive_detection"].values())
    n_bg = sum(cell["n"] for cell in row["background"].values())
    lines.append(f"- Background objects scored: {n_bg}. Of these, {none} had no positive detection and score 0.")
    inj = results.get("injection")
    if inj:
        curve = ", ".join(f"{b['peak_mag']:.1f}: {_share(b['recovered'], b['n'])}" for b in inj["bins"])
        lines.append(f"- Synthetic flares passing at that score, by peak magnitude, under a model cadence ({inj['cadence_model']}): {curve}.")
    else:
        lines.append("- Injection: not run.")
    return "\n".join(lines) + "\n"
