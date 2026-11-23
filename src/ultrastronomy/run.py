"""A run directory: the plan, its lock, where the data came from, what was computed.

    plan.json        written by the participant or their agent, before any data
    plan.lock        hash of the plan, of the code and of the mission files, with a timestamp
    provenance.json  every object used: source, retrieval time, content hash
    results.json     numbers computed by this program, never typed by an agent
    measured.md      the results as sentences, written by this program
    claims.json      statements by the agent, each tagged inferred / unverified
    report.md        measured.md verbatim, then the agent's inferences and what was not verified
    log.jsonl        every harness command that touched the run, failures included
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import score
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


# The modules that turn a plan into numbers. A change to any of them, or to a
# mission file, makes an older record impossible to recompute with this code.
# The gates, the command line and this file are not in the list: tightening a
# check must not invalidate the records it checks.
COMPUTE = ("lightcurve.py", "score.py", "intervals.py", "synth.py", "fink.py", "mission.py")


def changed_since_lock(record: dict, mission_dir: Path) -> list[str]:
    now_hashes = code_hashes(mission_dir)
    keys = [k for k in now_hashes if k in COMPUTE or k.startswith("mission/")]
    return sorted(k for k in keys if record["code_sha256"].get(k) != now_hashes[k])


def code_hashes(mission_dir: Path | None = None) -> dict:
    """Hashes of everything that turns a plan into numbers: the package and the mission files."""
    package = Path(__file__).parent
    hashes = {p.name: file_sha256(p) for p in sorted(package.glob("*.py"))}
    if mission_dir:
        hashes.update({f"mission/{p.name}": file_sha256(p) for p in sorted(mission_dir.iterdir())
                       if p.suffix in (".json", ".tsv")})
    return hashes


def git_commit() -> str:
    """The commit of the checkout, so a reviewer can get the same code. Empty outside git."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(Path(__file__).parent), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_time(stamp) -> float:
    """Seconds since the epoch for a harness timestamp. Raises on anything else."""
    from datetime import datetime, timezone
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


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
        "data": {"source": source, "seed": None, "weeks": 6, "per_class": 2, "max_requests": 130},
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
    record = {"plan_sha256": file_sha256(run / "plan.json"), "code_sha256": code_hashes(mission["dir"]),
              "git_commit": git_commit(), "locked_at": now()}
    write_json(run / "plan.lock", record)
    log(run, "lock", **record)
    return record


def require_lock(run: Path, mission: dict) -> dict:
    """The lock, after checking that neither the plan nor the code moved since."""
    if not (run / "plan.lock").exists():
        raise ValueError("plan is not locked. Run `ultra lock` before touching data.")
    record = read_json(run / "plan.lock")
    if file_sha256(run / "plan.json") != record["plan_sha256"]:
        raise ValueError("plan.json changed after it was locked. Start a new run instead.")
    changed = changed_since_lock(record, mission["dir"])
    if changed:
        raise ValueError(f"changed since the plan was locked: {changed}. "
                         f"Check out commit {record.get('git_commit') or '(unknown)'} or start a new run.")
    return record
