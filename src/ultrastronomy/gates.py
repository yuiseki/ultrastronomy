"""Gates: checks a run must pass before its record is shared.

A gate never repairs anything. It says what is wrong and the run stays
unshared until the cause is fixed. Thresholds are not loosened to pass.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import fink
from .mission import decide
from .run import code_hashes, file_sha256, read_json

CLAIM_KINDS = {"measured", "inferred", "unverified"}
REPORT_SECTIONS = ["## Measured", "## Inferred", "## Not verified"]
# Words that turn a candidate into an announcement. "rediscovery" and
# "re-found" are fine: the objects in this mission are already known.
OVERCLAIM = re.compile(
    r"\b(discover(y|ed|ies|s)?|confirm(ed|s|ation)?|"
    r"new (object|transient|tde|source|planet|star|class)|first (detection|observation))\b",
    re.IGNORECASE)
MIN_INJECTIONS_PER_BIN = 20


def _resolve(data, pointer: str):
    """Follow a JSON pointer such as /decision/positives_passed."""
    node = data
    for part in pointer.strip("/").split("/"):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def _gate(name, passed, detail=""):
    return {"gate": name, "passed": bool(passed), "detail": detail}


def run_gates(run: Path, mission: dict, cache: Path | None = None) -> list[dict]:
    gates = []
    have = {name: (run / name).exists() for name in
            ("plan.json", "plan.lock", "provenance.json", "results.json", "claims.json", "report.md")}

    # 1. The plan was fixed, and neither it nor the scoring code moved afterwards.
    if not (have["plan.json"] and have["plan.lock"]):
        gates.append(_gate("plan_locked", False, "plan.json or plan.lock is missing"))
        return gates
    plan, lock = read_json(run / "plan.json"), read_json(run / "plan.lock")
    gates.append(_gate("plan_locked", file_sha256(run / "plan.json") == lock["plan_sha256"],
                       "plan.json differs from the hash in plan.lock"))
    gates.append(_gate("code_unchanged", code_hashes() == lock["code_sha256"],
                       "score.py or lightcurve.py differs from the hashes in plan.lock"))

    if not (have["provenance.json"] and have["results.json"]):
        gates.append(_gate("results_present", False, "run `ultra fetch` and `ultra evaluate` first"))
        return gates
    provenance, results = read_json(run / "provenance.json"), read_json(run / "results.json")

    # 2. No data was read by this run before the plan was locked.
    early = [p["object_id"] for p in provenance if p["accessed_at"] < lock["locked_at"]]
    gates.append(_gate("locked_before_data", not early, f"read before the lock: {early[:5]}"))

    # 3. Every scored object has a provenance record, and cached data still matches it.
    known = {p["object_id"]: p for p in provenance}
    scored = [o["id"] for o in results["objects"]]
    missing = [i for i in scored if i not in known]
    changed = []
    if cache and plan["data"]["source"] == "fink":
        for p in provenance:
            path = cache / "objects" / f"{p['object_id']}.json"
            if path.exists() and fink.sha256_rows(read_json(path)["rows"]) != p["sha256"]:
                changed.append(p["object_id"])
    gates.append(_gate("provenance_complete", not missing and not changed,
                       f"no provenance: {missing[:5]}; content changed: {changed[:5]}"))

    # 4. Only allow-listed columns went into the score.
    extra = sorted(set(results["columns_used"]) - set(fink.COLUMNS))
    gates.append(_gate("no_leaky_columns", not extra, f"columns outside the allow-list: {extra}"))

    # 5. Every known object of the mission was scored; none was quietly dropped.
    if plan["data"]["source"] == "fink":
        wanted = {t["ztf_id"] for t in mission["truth"]}
        got = {o["id"] for o in results["objects"] if o["role"] == "truth"}
        gates.append(_gate("known_objects_scored", wanted == got, f"not scored: {sorted(wanted - got)}"))
    else:
        gates.append(_gate("known_objects_scored", any(o["role"] == "truth" for o in results["objects"]),
                           "no known objects in the results"))

    # 6. The verdict is the one the locked rule gives for the stored counts.
    d = results["decision"]
    again = decide(d["positives_passed"], d["positives_n"], d["background_passed"], d["background_n"])
    same_rule = (d["threshold"], d["primary_stratum"]) == (
        plan["decision_rule"]["threshold"], plan["decision_rule"]["primary_stratum"])
    gates.append(_gate("verdict_by_rule", same_rule and again["verdict"] == d["verdict"],
                       "the stored verdict is not what the locked rule gives"))

    # 7. Sensitivity was measured with injected sources.
    inj = results.get("injection")
    ok = bool(inj) and inj["threshold"] == d["threshold"] and all(b["n"] >= MIN_INJECTIONS_PER_BIN for b in inj["bins"])
    gates.append(_gate("injection_recovery", ok, "run `ultra inject`"))

    # 8. Each statement says what kind it is; measured ones point at a computed number.
    if not have["claims.json"]:
        gates.append(_gate("claims_traceable", False, "claims.json is missing"))
        claims = []
    else:
        claims, problems = read_json(run / "claims.json"), []
        if not isinstance(claims, list) or not claims:
            problems.append("claims.json must be a non-empty list")
            claims = []
        for i, c in enumerate(claims):
            if c.get("kind") not in CLAIM_KINDS:
                problems.append(f"claim {i}: kind must be one of {sorted(CLAIM_KINDS)}")
            elif c["kind"] == "measured":
                try:
                    actual = _resolve(results, c["evidence"])
                except (KeyError, IndexError, ValueError, TypeError):
                    problems.append(f"claim {i}: evidence {c.get('evidence')!r} is not in results.json")
                    continue
                if actual != c.get("value"):
                    problems.append(f"claim {i}: says {c.get('value')!r}, results.json has {actual!r}")
            elif not str(c.get("basis", "")).strip():
                problems.append(f"claim {i}: an {c['kind']} claim needs a `basis`")
        if claims and not any(c.get("kind") == "measured" for c in claims):
            problems.append("no measured claim: state at least the verdict")
        gates.append(_gate("claims_traceable", not problems, "; ".join(problems[:6])))

    # 9. The write-up keeps the three kinds apart and does not announce anything.
    if not have["report.md"]:
        gates.append(_gate("no_overclaim", False, "report.md is missing"))
    else:
        text = (run / "report.md").read_text(encoding="utf-8")
        absent = [s for s in REPORT_SECTIONS if s not in text]
        words = sorted({m.group(0).lower() for m in OVERCLAIM.finditer(text)} |
                       {m.group(0).lower() for c in claims for m in OVERCLAIM.finditer(str(c.get("text", "")))})
        gates.append(_gate("no_overclaim", not absent and not words,
                           f"missing sections: {absent}; announcement words: {words}. "
                           "Say 're-found' or 'candidate', and move anything unchecked under '## Not verified'."))
    return gates
