"""Clients for the two services of the periods mission, with the same cache and budget as Fink.

IRSA serves ZTF's public light curves; VSX is the AAVSO's index of known
variable stars. Neither needs an account. Both are asked for small cones only.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import fink

IRSA = "https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves"
VSX = "https://vsx.aavso.org/index.php"
# Bit 15 of catflags marks photometry ZTF itself calls unusable (clouds, moon).
BAD_CATFLAGS_MASK = 32768


def _get(url: str, params: dict, budget: fink.Budget, timeout: float = 180.0) -> bytes:
    budget.spend()
    full = url + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    req = urllib.request.Request(full, headers={"User-Agent": fink.USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    time.sleep(fink.PAUSE_SECONDS)
    return body


def _key(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def light_curves(ra: float, dec: float, radius_deg: float, cache: Path, budget, until_mjd: float) -> dict:
    """Every r-band ZTF light curve within a cone, keyed by ZTF's object id.

    Epochs after `until_mjd` are dropped and the rest sorted, so that a later
    data release gives the same rows for the same request.
    """
    def fetch():
        if budget is None:
            raise FileNotFoundError(f"light curves at {ra}, {dec} are not in the cache")
        params = {"POS": f"CIRCLE {ra} {dec} {radius_deg}", "BANDNAME": "r", "FORMAT": "csv",
                  "BAD_CATFLAGS_MASK": BAD_CATFLAGS_MASK}
        text = _get(IRSA, params, budget).decode("utf-8", errors="replace")
        if not text.lstrip().startswith("oid,"):
            raise RuntimeError(f"IRSA did not return a table: {text[:200]!r}")
        curves: dict[str, dict] = {}
        for row in csv.DictReader(io.StringIO(text)):
            mjd = float(row["mjd"])
            if mjd >= until_mjd:
                continue
            c = curves.setdefault(row["oid"], {"ra": float(row["ra"]), "dec": float(row["dec"]), "rows": []})
            c["rows"].append([mjd, float(row["mag"]), float(row["magerr"])])
        for c in curves.values():
            c["rows"].sort()
        return {"source": IRSA, "request": params, "until_mjd": until_mjd,
                "retrieved_at": fink.now(), "curves": dict(sorted(curves.items()))}
    return fink._cached(cache / "cones" / f"{_key(ra, dec, radius_deg, until_mjd)}.json", fetch)


def known_variables(ra: float, dec: float, radius_deg: float, cache: Path, budget, max_oid: int) -> dict:
    """VSX entries within a cone. Entries added after the mission was set up are ignored.

    VSX numbers its entries as they are added. Keeping only those up to
    `max_oid` makes the list repeatable while the catalogue grows. An entry
    that is revised or removed later will still change it.
    """
    def fetch():
        if budget is None:
            raise FileNotFoundError(f"the VSX list at {ra}, {dec} is not in the cache")
        params = {"view": "api.list", "ra": ra, "dec": dec, "radius": radius_deg, "format": "json"}
        data = json.loads(_get(VSX, params, budget))
        raw = data.get("VSXObjects", {})
        raw = raw.get("VSXObject", []) if isinstance(raw, dict) else []
        stars = []
        for o in raw if isinstance(raw, list) else [raw]:
            oid = int(o["OID"])
            if oid > max_oid:
                continue
            stars.append({"oid": oid, "name": o.get("Name", ""), "ra": float(o["RA2000"]),
                          "dec": float(o["Declination2000"]), "period": o.get("Period"),
                          "max_mag": o.get("MaxMag", ""), "discoverer": o.get("Discoverer", ""),
                          "category": o.get("Category", ""), "type": o.get("VariabilityType", "")})
        stars.sort(key=lambda s: s["oid"])
        return {"source": VSX, "request": params, "max_oid": max_oid, "retrieved_at": fink.now(), "stars": stars}
    return fink._cached(cache / "vsx" / f"{_key(ra, dec, radius_deg, max_oid)}.json", fetch)
