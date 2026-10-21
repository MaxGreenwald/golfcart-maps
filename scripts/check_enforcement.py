#!/usr/bin/env python3
"""Local-enforcement gate (added Oct 21 2026 after the 30A miss: the Walton County Sheriff's LSV bans lived only on
the sheriff's map image, so the build never saw them).

Every live (non-hidden) region in public/data/regions.json must have an "enforcement" record in
research/regions/<id>.json saying its local enforcement source (sheriff, police, or city/county golf cart or LSV map or
road list) was found and checked before it went live:

  "enforcement": {
    "checked": "YYYY-MM-DD",                        # date someone read the source
    "result": "bans_applied" | "none_found" | "bans_pending",
    "sources": [{"label": "...", "url": "https://..."}],   # at least one link
    "note": "...",                                  # what the source says / why nothing applied
    "missing": ["..."]                              # bans_pending only: road, source, what we show today
  }

bans_applied = the source's bans/designations are in the region's data. none_found = searched, no local list beyond
state law (note says what was searched). bans_pending = the source lists bans we don't model yet; allowed (the
region was already live), but listed on every run until fixed. --strict also fails on bans_pending.
This check is about the record existing; it does not change how any road is colored."""
import datetime, json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RESULTS = ("bans_applied", "none_found", "bans_pending")


def live_regions():
    return [r["id"] for r in json.load(open(os.path.join(ROOT, "public", "data", "regions.json"))) if not r.get("hidden")]


def record(rid):
    p = os.path.join(ROOT, "research", "regions", rid + ".json")
    return json.load(open(p)).get("enforcement") if os.path.exists(p) else None


def problems(rid, rec, today=None):
    if not rec: return [f"{rid}: no enforcement record in research/regions/{rid}.json (find and check the sheriff/police/city cart map or road list first)"]
    out = []
    try:
        d = datetime.date.fromisoformat(str(rec.get("checked", "")))
        if d > (today or datetime.date.today()): out.append(f"{rid}: enforcement.checked {d} is in the future")
    except ValueError:
        out.append(f"{rid}: enforcement.checked must be a YYYY-MM-DD date")
    if rec.get("result") not in RESULTS: out.append(f"{rid}: enforcement.result must be one of {RESULTS}")
    srcs = rec.get("sources") or []
    if not any(isinstance(s, dict) and re.match(r"https?://", s.get("url", "")) and s.get("label") for s in srcs):
        out.append(f"{rid}: enforcement.sources needs at least one {{label, url}} with an http(s) link")
    if not (rec.get("note") or "").strip(): out.append(f"{rid}: enforcement.note is required (what the source says, or what was searched)")
    if rec.get("result") == "bans_pending" and not rec.get("missing"): out.append(f"{rid}: bans_pending needs a 'missing' list")
    return out


def main(argv):
    strict = "--strict" in argv
    bad, pending = [], []
    for rid in live_regions():
        rec = record(rid); p = problems(rid, rec); bad += p
        if not p and rec["result"] == "bans_pending": pending.append((rid, rec["missing"]))
    for b in bad: print("FAIL enforcement", b)
    for rid, miss in pending:
        print(f"PEND enforcement {rid}: {len(miss)} source-listed ban(s) not in the data yet")
        for m in miss: print("       -", m)
    if strict and pending: bad.append("pending")
    print("ENFORCEMENT", "OK" if not bad else "FAIL", f"({len(live_regions())} live regions, {len(pending)} with pending bans)")
    return 1 if bad else 0


if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
