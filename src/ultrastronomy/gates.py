"""Gates: checks a run must pass before its record is shared.

What the gates are for: catching the mistakes of an agent that is trying to
do the right thing, and making a reviewer's check a single command. They
recompute every number from the data instead of trusting what is stored.

What they are not: a defence against someone who edits files by hand to
deceive. A record is only as good as its recomputation by another person
from data they fetched themselves (`ultra verify --refetch`).

A gate never repairs anything, and thresholds are not loosened to pass.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from . import fink
from . import mission as M
from .run import code_hashes, file_sha256, parse_time, read_json

CLAIM_KINDS = {"inferred", "unverified"}
REPORT_SECTIONS = ["Measured", "Inferred", "Not verified"]
OBJECT_ID = re.compile(r"ZTF\d{2}[a-z]{7}|SYN-[A-Z]+-\d{3}")
# A lint, not a guarantee: it catches the common ways of announcing a find and
# is easy to evade on purpose. It cannot tell a denial from an announcement.
ANNOUNCEMENT = re.compile(
    r"\b(discover\w*|confirm\w*|novel|bona fide|genuine|proven|proof|"
    r"(previously|hitherto) (unknown|uncatalogu?ed|unreported)|newly (found|identified|detected)|"
    r"new (object|transient|tde|source|planet|star|class|event)|"
    r"(for the )?first (time|detection|observation)|verified as|establish(es|ed)? (it|this|that)|"
    r"we (report|announce|present) a)\b", re.IGNORECASE)


def _plain(text: str) -> str:
    """Text with formatting tricks removed, so that the lint sees the words."""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return re.sub(r"\s+", " ", re.sub(r"[*_`~]", "", text))


def report_sections(text: str) -> list[tuple[str, str]]:
    """(heading, body) for every '## ' heading at the start of a line, in order."""
    out, heading, body = [], None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if heading is not None:
                out.append((heading, "\n".join(body).strip()))
            heading, body = line[3:].strip(), []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        out.append((heading, "\n".join(body).strip()))
    return out


def _gate(name, passed, detail=""):
    return {"gate": name, "passed": bool(passed), "detail": "" if passed else detail}


def run_gates(run: Path, mission: dict, cache: Path | None = None) -> list[dict]:
    gates = []
    for name in ("plan.json", "plan.lock", "log.jsonl"):
        if not (run / name).exists():
            return [_gate("plan_locked", False, f"{name} is missing")]
    plan, lock = read_json(run / "plan.json"), read_json(run / "plan.lock")
    events = [json.loads(line) for line in (run / "log.jsonl").read_text(encoding="utf-8").splitlines()]

    # 1. The plan is the one that was locked.
    gates.append(_gate("plan_locked", file_sha256(run / "plan.json") == lock["plan_sha256"],
                       "plan.json differs from the hash in plan.lock"))

    # 2. The code and the mission files are the ones that were locked.
    changed = sorted(k for k, v in code_hashes(mission["dir"]).items() if lock["code_sha256"].get(k) != v)
    gates.append(_gate("code_unchanged", not changed,
                       f"differs from the lock: {changed}. To check this record, use commit "
                       f"{lock.get('git_commit') or '(not recorded)'}"))

    # 3. The log shows one lock, made before any data step. The log is written by
    #    the harness but lives next to the run, so this is evidence, not proof.
    names = [e["event"] for e in events]
    data_steps = [i for i, n in enumerate(names) if n in ("sample", "fetch", "evaluate")]
    one_lock = names.count("lock") == 1 and (not data_steps or names.index("lock") < data_steps[0])
    gates.append(_gate("locked_once_before_data", one_lock,
                       f"the log has {names.count('lock')} lock events, or a data step before the lock"))

    if not ((run / "provenance.json").exists() and (run / "results.json").exists()):
        gates.append(_gate("results_present", False, "run `ultra fetch` and `ultra evaluate` first"))
        return gates
    provenance, results = read_json(run / "provenance.json"), read_json(run / "results.json")

    # 4. Every object was read after the lock.
    try:
        locked = parse_time(lock["locked_at"])
        early = [p["object_id"] for p in provenance if parse_time(p["accessed_at"]) < locked]
        gates.append(_gate("read_after_lock", not early, f"read before the lock: {early[:5]}"))
    except (ValueError, TypeError, KeyError) as e:
        gates.append(_gate("read_after_lock", False, f"a timestamp is not in the harness's format: {e}"))

    # 5. The data is here, matches its recorded hashes, and holds only allow-listed columns.
    try:
        objects = M.load_objects(plan, provenance, cache or Path("/nonexistent"))
    except FileNotFoundError:
        gates.append(_gate("data_matches_provenance", False,
                           "the data is not on this machine, so nothing below could be recomputed. "
                           "Run `ultra verify <record> --refetch --confirm`"))
        return gates
    except ValueError as e:
        gates.append(_gate("data_matches_provenance", False, str(e)))
        return gates
    gates.append(_gate("data_matches_provenance", True))
    extra = sorted({k for rows in objects.values() for r in rows for k in r} - set(fink.COLUMNS))
    gates.append(_gate("no_leaky_columns", not extra, f"columns outside the allow-list in the data: {extra}"))

    # 6. Every known object of the mission was scored; none was quietly dropped.
    wanted = {t["ztf_id"] for t in mission["truth"]}
    got = {p["object_id"] for p in provenance if p["role"] == "truth"}
    ok = wanted == got if plan["data"]["source"] == "fink" else bool(got)
    gates.append(_gate("known_objects_scored", ok, f"not scored: {sorted(wanted - got)}"))

    # 7. Recomputing from the data and the locked plan gives exactly the stored results.
    again = M.compute(objects, provenance, plan, mission, with_injection=True)
    differing = sorted(k for k in set(again) | set(results) if again.get(k) != results.get(k))
    gates.append(_gate("results_recomputed", not differing,
                       f"results.json differs from a recomputation in: {differing}. Run `ultra evaluate` again; do not edit it"))

    # 8. The Measured section is the program's text, unchanged.
    measured = M.measured_markdown(again).strip()
    report = (run / "report.md").read_text(encoding="utf-8") if (run / "report.md").exists() else ""
    sections = report_sections(report)
    headings = [h for h, _ in sections]
    body = dict(sections)
    gates.append(_gate("measured_is_generated", body.get("Measured", "").strip() == measured,
                       "the text under '## Measured' must be measured.md, unchanged. Put your own words under '## Inferred'"))

    # 9. The report has the three sections, in order, and keeps objects out of the inferences.
    problems = []
    if headings != REPORT_SECTIONS:
        problems.append(f"the '## ' headings must be exactly {REPORT_SECTIONS}, in that order; found {headings}")
    for name in ("Inferred", "Not verified"):
        if not body.get(name, "").strip():
            problems.append(f"'## {name}' is empty")
    named = sorted(set(OBJECT_ID.findall(body.get("Inferred", ""))))
    if named:
        problems.append(f"'## Inferred' names objects {named}: an individual object belongs under '## Not verified'")
    gates.append(_gate("report_structure", not problems, "; ".join(problems)))

    # 10. Every statement of the agent says what kind it is and what it rests on.
    problems, claims = [], []
    if not (run / "claims.json").exists():
        problems.append("claims.json is missing")
    else:
        claims = read_json(run / "claims.json")
        if not isinstance(claims, list) or not claims:
            problems, claims = ["claims.json must be a non-empty list"], []
        for i, c in enumerate(claims):
            if not isinstance(c, dict) or set(c) != {"kind", "text", "basis"}:
                problems.append(f"claim {i}: needs exactly the keys kind, text, basis")
            elif c["kind"] not in CLAIM_KINDS:
                problems.append(f"claim {i}: kind must be one of {sorted(CLAIM_KINDS)}; measured statements are in measured.md")
            elif not str(c["text"]).strip() or not str(c["basis"]).strip():
                problems.append(f"claim {i}: text and basis must not be empty")
        if claims and not any(isinstance(c, dict) and c.get("kind") == "unverified" for c in claims):
            problems.append("no unverified claim: every run leaves something unchecked")
    gates.append(_gate("claims_labelled", not problems, "; ".join(problems[:6])))

    # 11. Lint for announcement wording in everything the agent wrote.
    written = [body.get("Inferred", ""), body.get("Not verified", "")]
    written += [str(v) for c in claims if isinstance(c, dict) for v in c.values()]
    words = sorted({m.group(0).lower() for text in written for m in ANNOUNCEMENT.finditer(_plain(text))})
    gates.append(_gate("wording_lint", not words,
                       f"announcement wording: {words}. This check cannot tell a denial from an announcement. "
                       "Do not reword until it passes: say what was measured and what was not checked, without these words"))
    return gates
