"""Mission kind `periods`: re-find the catalogued periods of known variable stars.

One function, `derive`, turns a locked plan into the sample and its data.
The fetch, the evaluation and the gates all call it, so there is one place
where it is decided which stars are looked at.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from pathlib import Path

from . import catalogues, fink, periods
from .mission import decide

ELSEWHERE = "catalogued, found elsewhere"
BY_ZTF = "catalogued, found by ZTF"
NOT_CATALOGUED = "not catalogued"
EXPONENTS = [3, 5, 10, 20]            # a period is "flagged" when its false-alarm probability is below 10^-e
AMPLITUDES = [0.02, 0.05, 0.1, 0.2]   # magnitudes, for the injection
KNOWN_RADIUS_DEG = 0.0005             # 1.8 arcsec: the ZTF source at a catalogued position
EXCLUSION_ARCSEC = 5.0                # a background star may not be this close to a catalogued variable
MAG_RANGE = (13.5, 19.0)              # brighter saturates in ZTF, fainter is mostly noise
PERIOD_RANGE = (0.11, 90.0)           # inside the searched range, with a margin


def patch_centres(seed: int, n: int) -> list[tuple[float, float]]:
    """Random points on the part of the sky ZTF covers well, uniform in area."""
    rng = random.Random(seed)
    lo, hi = math.sin(math.radians(-20)), math.sin(math.radians(80))
    return [(round(rng.uniform(0, 360), 4), round(math.degrees(math.asin(rng.uniform(lo, hi))), 4)) for _ in range(n)]


def _first_number(text) -> float | None:
    for token in str(text).replace("(", " ").replace(")", " ").split():
        try:
            return float(token)
        except ValueError:
            continue
    return None


def _usable(star: dict) -> float | None:
    """The catalogued period, if this entry is a variable this search could recover."""
    period, mag = _first_number(star["period"]), _first_number(star["max_mag"])
    if star["category"] != "Variable" or period is None or mag is None:
        return None
    if not (PERIOD_RANGE[0] <= period <= PERIOD_RANGE[1] and MAG_RANGE[0] <= mag <= MAG_RANGE[1]):
        return None
    return period


def _arcsec(ra1, dec1, ra2, dec2) -> float:
    return 3600 * math.hypot((ra1 - ra2) * math.cos(math.radians(dec1)), dec1 - dec2)


def until_mjd(mission: dict) -> float:
    return fink.date_to_jd(mission["light_curves_until"]) - 2400000.5


def derive(plan: dict, mission: dict, cache: Path, budget, note=lambda **_: None) -> list[dict]:
    """The sample the plan selects, with its data. `budget=None` reads the cache only."""
    d = plan["data"]
    rng = random.Random(d["seed"])
    limit = until_mjd(mission)
    items, taken = [], set()   # patches can overlap: no star is taken twice
    for index, (ra, dec) in enumerate(patch_centres(d["seed"], d["patches"])):
        patch = f"{index}: {ra} {dec}"
        listing = catalogues.known_variables(ra, dec, mission["patch_radius_deg"], cache, budget, mission["vsx_max_oid"])
        stars = listing["stars"]
        pools = {ELSEWHERE: [], BY_ZTF: []}
        for star in stars:
            if _usable(star) is not None and f"VSX-{star['oid']}" not in taken:
                by_ztf = "ztf" in star["discoverer"].lower() or "zwicky" in star["discoverer"].lower()
                pools[BY_ZTF if by_ztf else ELSEWHERE].append(star)
        for label in (ELSEWHERE, BY_ZTF):
            picked = rng.sample(pools[label], min(d["per_stratum"], len(pools[label])))
            note(patch=patch, stratum=label, available=len(pools[label]), picked=[s["oid"] for s in picked])
            for star in picked:
                taken.add(f"VSX-{star['oid']}")
                cone = catalogues.light_curves(star["ra"], star["dec"], KNOWN_RADIUS_DEG, cache, budget, limit)
                # Several ZTF fields can cover one star: take the longest light curve.
                best = max(cone["curves"].items(), key=lambda kv: (len(kv[1]["rows"]), -int(kv[0])), default=None)
                items.append({"object_id": f"VSX-{star['oid']}", "role": "truth", "label": label, "patch": patch,
                              "data": {"rows": best[1]["rows"] if best else [], "cat_period": _usable(star)},
                              "source": cone["source"], "retrieved_at": cone["retrieved_at"]})
        cone = catalogues.light_curves(ra, dec, mission["background_radius_deg"], cache, budget, limit)
        free = sorted(oid for oid, c in cone["curves"].items()
                      if len(c["rows"]) >= periods.MIN_POINTS and f"ZTFDR-{oid}" not in taken
                      and all(_arcsec(c["ra"], c["dec"], s["ra"], s["dec"]) > EXCLUSION_ARCSEC for s in stars))
        picked = rng.sample(free, min(d["per_stratum"], len(free)))
        note(patch=patch, stratum=NOT_CATALOGUED, available=len(free), picked=picked)
        for oid in picked:
            taken.add(f"ZTFDR-{oid}")
            items.append({"object_id": f"ZTFDR-{oid}", "role": "background", "label": NOT_CATALOGUED, "patch": patch,
                          "data": {"rows": cone["curves"][oid]["rows"], "cat_period": None},
                          "source": cone["source"], "retrieved_at": cone["retrieved_at"]})
    return items


def _flagged(best, exponent) -> bool:
    return best is not None and best["log10_fap"] < -exponent


def evaluate(objects: dict, provenance: list[dict], plan: dict, mission: dict) -> dict:
    e = plan["decision_rule"]["threshold"]
    order = sorted(provenance, key=lambda p: p["object_id"])

    # What will be injected into each background star is drawn first, amplitude by
    # amplitude and star by star, so that the draw does not depend on any result.
    rng = random.Random(plan["data"]["seed"])
    searchable = [p["object_id"] for p in order if p["role"] == "background"
                  and len(objects[p["object_id"]]["rows"]) >= periods.MIN_POINTS]
    drawn = {oid: [] for oid in searchable}
    for amplitude in AMPLITUDES:
        for oid in searchable:
            drawn[oid].append((amplitude, 10 ** rng.uniform(math.log10(PERIOD_RANGE[0]), math.log10(50.0)),
                               rng.uniform(0, 2 * math.pi)))

    scored, injected = [], {}
    for p in order:
        data = objects[p["object_id"]]
        times, mags = [r[0] for r in data["rows"]], [r[1] for r in data["rows"]]
        columns = [mags] + [[m + a * math.sin(2 * math.pi * t / period + phase) for t, m in zip(times, mags)]
                            for a, period, phase in drawn.get(p["object_id"], [])]
        best, *with_signal = periods.best_periods(times, columns) if times else [None]
        injected[p["object_id"]] = with_signal
        kind = periods.match(best["period"], data["cat_period"]) if best and data["cat_period"] else "none"
        scored.append({"id": p["object_id"], "role": p["role"], "label": p["label"],
                       "n_points": len(data["rows"]), "cat_period": data["cat_period"],
                       "period": best["period"] if best else None,
                       "log10_fap": best["log10_fap"] if best else None, "match": kind})

    labels = sorted({s["label"] for s in scored if s["role"] == "truth"})
    table = []
    for level in EXPONENTS:
        row = {"exponent": level, "known": {}, "background": {}}
        for label in labels:
            members = [s for s in scored if s["label"] == label]
            hits = [s for s in members if s["log10_fap"] is not None and s["log10_fap"] < -level and s["match"] != "none"]
            row["known"][label] = {"recovered": len(hits), "exact": sum(s["match"] == "exact" for s in hits), "n": len(members)}
        bg = [s for s in scored if s["role"] == "background"]
        row["background"][NOT_CATALOGUED] = {"flagged": sum(s["log10_fap"] is not None and s["log10_fap"] < -level for s in bg), "n": len(bg)}
        table.append(row)

    positives = [s for s in scored if s["role"] == "truth" and s["label"] in mission["positive_groups"]]
    background = [s for s in scored if s["role"] == "background"]
    hit = lambda s: s["log10_fap"] is not None and s["log10_fap"] < -e
    decision = {"threshold": e, "primary_stratum": NOT_CATALOGUED, **decide(
        sum(hit(s) and s["match"] != "none" for s in positives), len(positives),
        sum(hit(s) for s in background), len(background))}

    # Injection results count only stars the search left alone: a star that is
    # already flagged cannot show whether an added signal would have been found.
    quiet = [s["id"] for s in background if s["id"] in drawn and not hit(s)]
    injection = []
    for k, amplitude in enumerate(AMPLITUDES):
        recovered = sum(bool(_flagged(injected[oid][k], e)
                             and periods.match(injected[oid][k]["period"], drawn[oid][k][1]) != "none") for oid in quiet)
        injection.append({"amplitude": amplitude, "recovered": recovered, "n": len(quiet)})

    return {"data_source": plan["data"]["source"], "objects": scored, "table": table, "decision": decision,
            "injection": {"threshold": e, "on": "real r-band light curves of background stars that were not flagged",
                          "signal": "a sinusoid, period drawn log-uniformly from 0.11 to 50 days", "bins": injection}}


def measured_markdown(results: dict) -> str:
    d, e = results["decision"], results["decision"]["threshold"]
    row = next(r for r in results["table"] if r["exponent"] == e) if e in EXPONENTS else None
    lines = [
        "- Data: ZTF public r-band light curves from IRSA; known variables from the AAVSO VSX.",
        f"- Locked rule: a period is flagged when its false-alarm probability is below 10^-{e}; "
        f"variables catalogued without ZTF against stars not catalogued.",
        f"- Catalogued variables whose period was found (exactly, or at half or double): {d['positives_passed']} of {d['positives_n']}. "
        f"Stars not catalogued that were flagged: {d['background_passed']} of {d['background_n']}.",
    ]
    if d["ci95_low"] is None:
        lines.append(f"- Verdict: {d['verdict']} ({d['reason']}). No interval was computed.")
    else:
        lines.append(f"- Difference: {d['difference']:+.3f}, 95% interval {d['ci95_low']:+.3f} to {d['ci95_high']:+.3f}.")
        lines.append(f"- Verdict: {d['verdict']}.")
    for r in results["table"]:
        parts = [f"`{label}` {c['recovered']} of {c['n']} found ({c['exact']} at the exact period)" for label, c in r["known"].items()]
        bg = r["background"][NOT_CATALOGUED]
        lines.append(f"- At 10^-{r['exponent']}: " + "; ".join(parts) + f"; `{NOT_CATALOGUED}` {bg['flagged']} of {bg['n']} flagged.")
    short = sum(o["n_points"] < periods.MIN_POINTS for o in results["objects"])
    lines.append(f"- Stars with fewer than {periods.MIN_POINTS} epochs, which cannot be searched and count as not found: {short}.")
    inj = results["injection"]
    curve = ", ".join(f"{b['amplitude']} mag: {b['recovered']} of {b['n']}" for b in inj["bins"])
    lines.append(f"- Sinusoids added to {inj['on']}, found at the injected period, by amplitude: {curve}.")
    return "\n".join(lines) + "\n"


class Periods:
    cache_name = "periods"

    def planned_requests(self, plan, mission) -> int:
        d = plan["data"]
        return d["patches"] * (2 + 2 * d["per_stratum"])

    def fetch(self, run, plan, mission, cache, budget):
        from .run import log
        items = derive(plan, mission, cache, budget, note=lambda **f: log(run, "sample", **f))
        return [{"object_id": i["object_id"], "role": i["role"], "label": i["label"], "week": i["patch"],
                 "source": i["source"], "retrieved_at": i["retrieved_at"], "accessed_at": fink.now(),
                 "sha256": fink.sha256_rows(i["data"]), "n_alerts": len(i["data"]["rows"])} for i in items]

    def fetch_summary(self, plan, mission, provenance) -> str:
        got = Counter(p["label"] for p in provenance)
        want = plan["data"]["patches"] * plan["data"]["per_stratum"]
        lines = [f"Stars per group (asked for {want}):"]
        for label in (ELSEWHERE, BY_ZTF, NOT_CATALOGUED):
            note = "" if got[label] == want else "   <- fewer than asked: some patches had too few such stars"
            lines.append(f"  {label}: {got[label]}{note}")
        return "\n".join(lines)

    def load_objects(self, plan, provenance, cache):
        derived = {i["object_id"]: i["data"] for i in derive(plan, mission_of(plan), cache, None)}
        for p in provenance:
            if p["object_id"] in derived and fink.sha256_rows(derived[p["object_id"]]) != p["sha256"]:
                raise ValueError(f"{p['object_id']}: data no longer matches the hash in provenance.json")
        return derived

    def compute(self, objects, provenance, plan, mission):
        known = [p for p in provenance if p["object_id"] in objects]
        return evaluate(objects, known, plan, mission)

    def measured_markdown(self, results) -> str:
        return measured_markdown(results)

    def leaky_columns(self, objects) -> list[str]:
        return sorted({k for data in objects.values() for k in data} - {"rows", "cat_period"})

    def expected_sample(self, plan, mission, cache) -> list[tuple]:
        if cache is None:
            raise FileNotFoundError("no cache")
        return [(i["object_id"], i["role"], i["label"], i["patch"]) for i in derive(plan, mission, cache, None)]

    def refetch_count(self, plan, mission, provenance) -> int:
        return self.planned_requests(plan, mission)

    def refetch(self, plan, mission, provenance, cache, budget) -> None:
        derive(plan, mission, cache, budget)


def mission_of(plan: dict) -> dict:
    from .mission import load_mission
    return load_mission(plan["mission"])
