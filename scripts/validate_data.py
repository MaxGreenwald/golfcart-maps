#!/usr/bin/env python3
"""Data validation on the built tiles (public/data/<region>/tiles), no OSM cache needed. Run in CI and after builds.

Check "red island": a connected group of segments with NO known limit (speed 99, code 'i' = untagged major road)
whose every neighbouring road (cart paths ignored) is <=35 mph, at least one of them posted/verified. That pattern is how the
Villages roundabouts bug looked (a red ring between green 35 mph approaches). Such islands are usually a
data gap, not a real 40+ road, so they must be justified by the baseline file.

Check "ring code": segments with code 'r' (roundabout inherited) must carry a real speed (not 99/None).

Check "same-road island" (scripts/islands.py, added Oct 18 2026 after the Soledad Mountain Rd red stretch): a short (<0.5 mi)
red run of one road with the SAME road at <=35 on both ends, whatever its source (untagged, OSM tag, Mapillary, DOT, official).
Every one must be listed BY LOCATION in research/red_island_allowlist.json ("real" with a cite, or "unreviewed"); a count
baseline can't do this job because a new island hides behind a fixed one (that is how Soledad got past the count of 77).
The builders heal the clear cases themselves (islands.heal), so anything left needs a person: check the cite, then list it.

Exit 1 if any region has more red islands or ring-code errors than research/validation_baseline.json allows
(i.e. a new regression), or any same-road island that is not in the allowlist. Known, reviewed cases live in the baseline; lower it when data gets fixed. `--update-baseline` rewrites the baseline with today's counts (review the diff!)."""
import json, os, sys, glob, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import islands as ISL
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BASE = os.path.join(ROOT, "research", "validation_baseline.json")
ALLOW = os.path.join(ROOT, "research", "red_island_allowlist.json")
POSTED = set("tvmdrknq")   # tagged, verified, mapillary, designated, roundabout-/turn-lane-/same-road-inherited, sources-disagree
MAJOR_OK = ("motorway", "trunk")   # untagged freeways are legitimately red; ignore them

def load(region):
    segs = []
    for f in sorted(glob.glob(os.path.join(ROOT, "public", "data", region, "tiles", "*.json"))):
        segs += json.load(open(f))
    return segs

def red_islands(segs):
    """Return list of islands: {"n": segs, "names": [...], "at": [lat, lon], "neighbours": k}."""
    unk = [i for i, s in enumerate(segs) if s[2] == 99 and s[3] == "i" and not s[1].startswith(MAJOR_OK)]
    us = set(unk); bynode = {}
    for i, s in enumerate(segs):
        for n in (s[5], s[6]): bynode.setdefault(n, []).append(i)
    seen, out = set(), []
    for i in unk:
        if i in seen: continue
        comp, stack = [], [i]; seen.add(i)
        while stack:
            k = stack.pop(); comp.append(k)
            for n in (segs[k][5], segs[k][6]):
                for j in bynode[n]:
                    if j in us and j not in seen: seen.add(j); stack.append(j)
        cs = set(comp)
        nb = {j for k in comp for n in (segs[k][5], segs[k][6]) for j in bynode[n] if j not in cs and segs[j][3] != "c"}
        if len(nb) >= 2 and all(segs[j][2] is not None and segs[j][2] <= 35 for j in nb) and any(segs[j][3] in POSTED for j in nb):
            p = segs[comp[0]][7][0]
            out.append({"n": len(comp), "at": [p[1], p[0]], "neighbours": len(nb), "hw": segs[comp[0]][1]})
    return out

def ring_errors(segs):
    """'r' segments must carry a usable inherited speed (99 = inherited from a banned/unknown road: also an error)."""
    return [s[7][0] for s in segs if s[3] in ("r", "k") and (s[2] is None or s[2] > 35 and s[3] == "k" or s[2] == 99)]

def load_index(region):
    p = os.path.join(ROOT, "public", "data", region, "index.json")
    return json.load(open(p)) if os.path.exists(p) else {"names": [""], "sources": []}

def allowed(region, isl, allow, R=150):
    for a in allow:
        if a["region"] == region and a["road"] == isl["name"] and math.hypot((a["at"][0] - isl["at"][0]) * 110540, (a["at"][1] - isl["at"][1]) * 111320 * math.cos(math.radians(a["at"][0]))) <= R: return a
    return None

def same_road(region, segs, allow):
    ix = load_index(region); out = []
    for x in ISL.find(segs, ix["names"]):
        x["kind"] = ISL.kind(x, segs, ix["sources"]); x["allow"] = allowed(region, x, allow)
        x["src"] = sorted({ix["sources"][segs[k][8]][1][:120] for k in x["idx"] if len(segs[k]) > 8 and 0 <= segs[k][8] < len(ix["sources"])})
        out.append(x)
    return out

def main(argv):
    regions = [r["id"] for r in json.load(open(os.path.join(ROOT, "public", "data", "regions.json")))]
    only = [a for a in argv if not a.startswith("--")]
    if only: regions = [r for r in regions if r in only]
    base = json.load(open(BASE)) if os.path.exists(BASE) else {}
    bi, br = base.get("red_islands", {}), base.get("ring_code_errors", {})
    allow = json.load(open(ALLOW))["islands"] if os.path.exists(ALLOW) else []
    sr_all = {}
    counts, rcounts, bad = {}, {}, []
    for r in regions:
        segs = load(r)
        if not segs: continue
        isl, rer = red_islands(segs), ring_errors(segs)
        counts[r] = len(isl); rcounts[r] = len(rer); allowed = bi.get(r, 0); rallowed = br.get(r, 0)
        st = "FAIL" if len(isl) > allowed or len(rer) > rallowed else "ok"
        print(f"{st:4} {r:12} segments={len(segs):6} red_islands={len(isl)} (baseline {allowed}) ring_code_errors={len(rer)} (baseline {rallowed})")
        if len(isl) > allowed:
            for x in sorted(isl, key=lambda x: -x["neighbours"])[:10]: print("      island", x)
            bad.append(r)
        if len(rer) > rallowed: print("      ring segments with no usable speed at", rer[:5]); bad.append(r)
        sr = same_road(r, segs, allow); sr_all[r] = sr; new = [x for x in sr if not x["allow"]]
        print(f"     {'FAIL' if new else 'ok':4} same-road islands={len(sr)} (allowlisted {len(sr) - len(new)}, source-confirmed {sum(1 for x in sr if x['allow'] and x['allow'].get('status') in ('real', 'source-confirmed'))}, new {len(new)})")
        for x in new[:10]: print("      NEW same-road island:", {k: x[k] for k in ("name", "m", "hw", "codes", "mph_in", "mph_out", "kind", "at", "src")})
        if new: bad.append(r)
    if "--allowlist-unreviewed" in argv:   # list today's unlisted islands ("source-confirmed" keeps its data cite; review the diff!)
        for r, sr in sr_all.items():
            for x in sr:
                if not x["allow"]: allow.append({"region": r, "road": x["name"], "at": x["at"], "m": x["m"], "mph": x["mph_in"], "sides": x["mph_out"], "kind": x["kind"],
                                  "status": "source-confirmed" if x["kind"] == "confirmed" else "unreviewed", "cite": x["src"]})
        old = json.load(open(ALLOW)) if os.path.exists(ALLOW) else {}
        json.dump({"_note": old.get("_note", ""), "islands": allow}, open(ALLOW, "w"), indent=1); print("allowlist written", ALLOW)
    if "--report" in argv:
        rows = [(r, x) for r, sr in sr_all.items() for x in sr]
        print(json.dumps({r: len(sr) for r, sr in sr_all.items()}))
        json.dump([{"region": r, **{k: x[k] for k in ("name", "m", "hw", "codes", "mph_in", "mph_out", "kind", "at", "src")}, "status": (x["allow"] or {}).get("status", "NEW")} for r, x in rows],
                  open(os.path.join(ROOT, "research", "red_islands_report.json"), "w"), indent=1)
    if "--update-baseline" in argv:
        json.dump({**{k: v for k, v in base.items() if k not in ("red_islands", "ring_code_errors")}, "_note": base.get("_note", "Reviewed known cases. Fail = more than this. Lower when fixed; raise only after checking the listed islands."),
                   "red_islands": dict(sorted({**bi, **counts}.items())), "ring_code_errors": dict(sorted({**br, **{k: v for k, v in rcounts.items() if v}}.items()))},
                  open(BASE, "w"), indent=1); print("baseline written", BASE)
        return 0
    print("RESULT", "ALL OK" if not bad else "FAIL " + ",".join(sorted(set(bad))))
    return 1 if bad else 0

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
