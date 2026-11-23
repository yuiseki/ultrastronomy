"""A run directory: the plan, its lock, where the data came from, what was computed.

    plan.json        written by the participant or their agent, before any data
    plan.lock        hash of the plan and of the scoring code, with a timestamp
    provenance.json  every object used: source, retrieval time, content hash
    results.json     numbers computed by this program, never typed by an agent
    claims.json      statements by the agent, each tagged measured / inferred / unverified
    report.md        the agent's write-up
    log.jsonl        every harness command that touched the run, failures included
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import lightcurve, score
from .fink import now

REQUIRED_TEXT = ["claim", "rationale", "failure_interpretation", "seen_before_lock", "ai_budget"]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def log(run: Path, event: str, **fields) -> None:
    with (run / "log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": now(), "event": event, **fields}, ensure_ascii=False) + "\n")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_hashes() -> dict:
    """Hashes of the modules that turn photometry into a score."""
    return {name: file_sha256(Path(mod.__file__)) for name, mod in (("score", score), ("lightcurve", lightcurve))}


def new_plan(mission: dict, ai_budget: str, source: str = "fink") -> dict:
    return {
        "mission": mission["id"],
        "kind": "replication",
        "claim": "",
        "decision_rule": {"threshold": None, "primary_stratum": None},
        "rationale": "",
        "failure_interpretation": "",
        "alternative_explanations": [],
        "seen_before_lock": "",
        "ai_budget": ai_budget,
        "data": {"source": source, "seed": None, "weeks": 3, "per_class": 2, "max_requests": 80},
    }


def plan_problems(plan: dict, mission: dict) -> list[str]:
    """Why this plan cannot be locked yet. Empty when it can."""
    problems = [f"`{key}` is empty" for key in REQUIRED_TEXT if not str(plan.get(key, "")).strip()]
    rule = plan.get("decision_rule", {})
    threshold = rule.get("threshold")
    if not isinstance(threshold, int) or isinstance(threshold, bool) or not 1 <= threshold <= len(score.CRITERIA):
        problems.append(f"`decision_rule.threshold` must be an integer from 1 to {len(score.CRITERIA)}")
    if rule.get("primary_stratum") not in mission["strata"]:
        problems.append(f"`decision_rule.primary_stratum` must be one of {mission['strata']}")
    if not plan.get("alternative_explanations"):
        problems.append("`alternative_explanations` needs at least one entry")
    data = plan.get("data", {})
    if not isinstance(data.get("seed"), int) or isinstance(data.get("seed"), bool):
        problems.append("`data.seed` must be an integer you choose")
    for key in ("weeks", "per_class", "max_requests"):
        if not isinstance(data.get(key), int) or data.get(key) < 1:
            problems.append(f"`data.{key}` must be a positive integer")
    return problems


def lock(run: Path, mission: dict) -> dict:
    plan = read_json(run / "plan.json")
    problems = plan_problems(plan, mission)
    if problems:
        raise ValueError("plan is not ready to lock:\n  - " + "\n  - ".join(problems))
    if (run / "plan.lock").exists():
        raise ValueError("plan is already locked. Start a new run to change it.")
    record = {"plan_sha256": file_sha256(run / "plan.json"), "code_sha256": code_hashes(), "locked_at": now()}
    write_json(run / "plan.lock", record)
    log(run, "lock", **record)
    return record


def require_lock(run: Path) -> dict:
    """The lock, after checking that neither the plan nor the code moved since."""
    if not (run / "plan.lock").exists():
        raise ValueError("plan is not locked. Run `ultra lock` before touching data.")
    record = read_json(run / "plan.lock")
    if file_sha256(run / "plan.json") != record["plan_sha256"]:
        raise ValueError("plan.json changed after it was locked. Start a new run instead.")
    if code_hashes() != record["code_sha256"]:
        raise ValueError("score.py or lightcurve.py changed after the plan was locked.")
    return record
