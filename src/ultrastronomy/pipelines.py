"""One pipeline per kind of mission. The gates and the command line only talk to this.

A pipeline turns a locked plan into a sample, data, results and sentences, and
can do all of it again from the plan alone. That second ability is what the
gates rest on: nothing a run wrote down is taken as given.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import random
from collections import Counter
from pathlib import Path

from . import fink, synth
from . import mission as M
from .run import read_json


class Screen:
    """Mission kind `screen`: a fixed set of criteria scored on Fink alert photometry."""

    cache_name = "fink"

    def planned_requests(self, plan, mission) -> int:
        return M.planned_requests(plan, mission)

    def fetch(self, run, plan, mission, cache, budget):
        return M.fetch_fink(run, plan, mission, cache, budget)

    def fetch_summary(self, plan, mission, provenance) -> str:
        got = Counter(p["label"] for p in provenance if p["role"] == "background")
        want = plan["data"]["weeks"] * plan["data"]["per_class"]
        lines = [f"Background objects per stratum (asked for {want}):"]
        for stratum in mission["strata"]:
            note = "" if got[stratum] == want else "   <- fewer than asked: some weeks returned nothing for this class"
            lines.append(f"  {stratum}: {got[stratum]}{note}")
        lines.append("An empty week is usually a week without observations, or a class label Fink no longer uses.")
        return "\n".join(lines)

    def load_objects(self, plan, provenance, cache):
        return M.load_objects(plan, provenance, cache)

    def compute(self, objects, provenance, plan, mission):
        return M.compute(objects, provenance, plan, mission, with_injection=True)

    def measured_markdown(self, results) -> str:
        return M.measured_markdown(results)

    def leaky_columns(self, objects) -> list[str]:
        return sorted({k for rows in objects.values() for r in rows for k in r} - set(fink.COLUMNS))

    def expected_sample(self, plan, mission, cache) -> list[tuple]:
        """(object, role, label, week) for every object the locked plan selects.

        Repeats the selection of `mission.fetch_fink` without reading
        provenance.json. A test keeps the two in step.
        """
        d = plan["data"]
        if d["source"] == "synthetic":
            _, truth, background = synth.demo_population(d["seed"])
            return ([(t["ztf_id"], "truth", t["group"], "") for t in truth] +
                    [(b["ztf_id"], "background", b["stratum"], "") for b in background])
        if cache is None:
            raise FileNotFoundError("no cache")
        rng = random.Random(d["seed"])
        truth_ids = {t["ztf_id"] for t in mission["truth"]}
        out = [(t["ztf_id"], "truth", t["group"], "") for t in mission["truth"]]
        for week in M.sample_weeks(d["seed"], d["weeks"], mission["first_date"], mission["last_date"]):
            stop = (dt.date.fromisoformat(week) + dt.timedelta(days=7)).isoformat()
            for stratum in mission["strata"]:
                key = hashlib.sha256(f"{stratum}|{week}|{stop}|3000".encode()).hexdigest()[:16]
                entry = read_json(cache / "weeks" / f"{key}.json")
                taken = {o[0] for o in out}
                ids = [i for i in entry["ids"] if i not in truth_ids and i not in taken]
                out += [(oid, "background", stratum, week) for oid in rng.sample(ids, min(d["per_class"], len(ids)))]
        return out

    def refetch_count(self, plan, mission, provenance) -> int:
        return len(provenance) + plan["data"]["weeks"] * len(mission["strata"])

    def refetch(self, plan, mission, provenance, cache, budget) -> None:
        d = plan["data"]
        for week in M.sample_weeks(d["seed"], d["weeks"], mission["first_date"], mission["last_date"]):
            stop = (dt.date.fromisoformat(week) + dt.timedelta(days=7)).isoformat()
            for stratum in mission["strata"]:
                fink.class_week(stratum, week, stop, cache, budget)
        for p in provenance:
            fink.object_alerts(p["object_id"], cache, budget, mission["alerts_until"])


def pipeline(mission: dict):
    if mission.get("kind", "screen") == "periods":
        from .mission_periods import Periods
        return Periods()
    return Screen()
