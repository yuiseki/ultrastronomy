"""Minimal Fink/ZTF REST client: allow-listed columns, on-disk cache, request budget.

Only the columns in COLUMNS are ever requested, so later classifications
(`d:tns`, `d:cdsxmatch`, classifier scores) cannot leak into a screen that is
being tested against objects classified after the fact.

`columns` accepts `i:` and `d:` fields only. A `v:` field makes the server
answer 500 with no explanation.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.ztf.fink-portal.org/api/v1"
COLUMNS = [
    "i:objectId", "i:candid", "i:jd", "i:fid", "i:magpsf", "i:sigmapsf", "i:isdiffpos",
    "i:ra", "i:dec", "i:distpsnr1", "i:sgscore1",
]
PAUSE_SECONDS = 1.0
USER_AGENT = "ultrastronomy/0.1"


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """Counts network requests and refuses to go past the limit."""

    def __init__(self, max_requests: int):
        self.max_requests = max_requests
        self.used = 0

    def spend(self) -> None:
        if self.used >= self.max_requests:
            raise BudgetExceeded(f"request budget of {self.max_requests} is used up")
        self.used += 1


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_rows(rows) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _post(endpoint: str, payload: dict, budget: Budget, timeout: float = 300.0):
    budget.spend()
    req = urllib.request.Request(
        f"{API}/{endpoint}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    time.sleep(PAUSE_SECONDS)
    if not isinstance(data, list):
        raise RuntimeError(f"{endpoint} returned {str(data)[:200]}")
    return data


def _cached(path: Path, fetch):
    """Read a cache entry, or fetch it and write it. Returns the entry dict."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    entry = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry), encoding="utf-8")
    return entry


def object_alerts(object_id: str, cache: Path, budget: Budget) -> dict:
    """Cache entry for one object: rows plus where and when they came from."""
    def fetch():
        payload = {"objectId": object_id, "columns": ",".join(COLUMNS)}
        rows = _post("objects", payload, budget)
        return {"source": f"{API}/objects", "request": payload, "retrieved_at": now(), "rows": rows}
    return _cached(cache / "objects" / f"{object_id}.json", fetch)


def class_week(fink_class: str, start: str, stop: str, cache: Path, budget: Budget, n: int = 3000) -> dict:
    """Object ids with an alert of this Fink class in [start, stop).

    The server returns the last `n` alerts walking back from `stop`. A week
    with no observing night, and a class label that Fink stopped using, both
    come back as an empty list.
    """
    def fetch():
        payload = {"class": fink_class, "n": n, "startdate": start, "stopdate": stop, "columns": "i:objectId,i:jd"}
        rows = _post("latests", payload, budget)
        ids = sorted({r["i:objectId"] for r in rows})
        return {"source": f"{API}/latests", "request": payload, "retrieved_at": now(), "ids": ids}
    key = hashlib.sha256(f"{fink_class}|{start}|{stop}|{n}".encode()).hexdigest()[:16]
    return _cached(cache / "weeks" / f"{key}.json", fetch)
