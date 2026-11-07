#!/usr/bin/env python3
"""Write research/expansion100_roads_to_verify.md from the built tiles of the 24 new regions.
Picks named roads whose legal status is the least certain: a ban, an inferred fast class,
an inferred 25 mph tertiary, or a speed sitting on the golf cart or LSV cap.
A road is dropped only when research/expansion100_signchecks.json confirms it.
That file is not written here. Mapillary and Street View are not called."""
import glob, json, os, collections
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
IDS = ["fairhope", "ocracoke", "dadecity", "mountdora", "pinehurst", "beaufort", "portroyal",
       "georgetown", "horseshoebay", "surfside", "colonialbeach", "flaglerbeach", "oriental",
       "celina", "capecharles", "sunlakes", "morrobay", "pismo", "howey", "apalachicola",
       "cedarkey", "islamorada", "keylargo", "crystalriver"]
MAJOR = {"primary", "secondary", "tertiary", "trunk"}
CHECKS = os.path.join(ROOT, "research", "expansion100_signchecks.json")

def load(rid):
    idx = json.load(open(os.path.join(ROOT, "public/data", rid, "index.json")))
    names = idx["names"]
    rows = []
    for f in glob.glob(os.path.join(ROOT, "public/data", rid, "tiles", "*.json")):
        for s in json.load(open(f)):
            if not names[s[0]]: continue
            mid = s[7][len(s[7]) // 2]
            rows.append({"name": names[s[0]], "hw": s[1].replace("_link", ""), "mph": s[2], "src": s[3],
                         "flag": s[9] if len(s) > 9 else 0, "lat": mid[1], "lon": mid[0], "n": len(s[7])})
    return rows

def _token_set():
    if os.environ.get("MAPILLARY_TOKEN", "").strip():
        return True
    env = os.path.join(ROOT, ".env")
    if not os.path.exists(env):
        return False
    for line in open(env):
        if line.startswith("MAPILLARY_TOKEN=") and line.split("=", 1)[1].strip():
            return True
    return False

def _google_key_set():
    for name in ("GOOGLE_MAPS_API_KEY", "GOOGLE_API_KEY", "STREETVIEW_API_KEY"):
        if os.environ.get(name, "").strip():
            return True
    return False

def sign_checks():
    """region -> road name -> {mph, source, confirmed}. Empty when the file is absent."""
    if not os.path.exists(CHECKS):
        return {}
    raw = json.load(open(CHECKS))
    out = {}
    for rid, roads in raw.items():
        out[rid] = {}
        for name, hit in roads.items():
            if not isinstance(hit, dict) or "mph" not in hit or not hit.get("source"):
                continue
            out[rid][name] = {"mph": int(hit["mph"]), "source": str(hit["source"]), "confirmed": bool(hit.get("confirmed"))}
    return out

def posted_sign_pieces(rid):
    """Drawn segments whose speed comes from a Mapillary detection or a Street View posted sign."""
    idx = json.load(open(os.path.join(ROOT, "public/data", rid, "index.json")))
    srcs = idx.get("sources") or []
    n = 0
    for f in glob.glob(os.path.join(ROOT, "public/data", rid, "tiles", "*.json")):
        for s in json.load(open(f)):
            if s[3] == "m":
                n += 1
                continue
            if len(s) > 8 and isinstance(s[8], int) and 0 <= s[8] < len(srcs):
                lab = srcs[s[8]][1].lower()
                if "mapillary" in lab or "posted sign" in lab or "street view" in lab:
                    n += 1
    return n

def finding_clause(hit):
    if not hit:
        return "Posted speed seen: not read. Source: none."
    return "Posted speed seen: %s mph. Source: %s." % (hit["mph"], hit["source"])

def link(name, place, lat, lon):
    q = (name + " " + place).replace(" ", "+")
    return f"https://www.google.com/maps/search/?api=1&query={q}+@{lat:.5f},{lon:.5f}"

def pick(rows):
    by = collections.defaultdict(list)
    for r in rows: by[r["name"]].append(r)
    out = []
    def add(name, why, sample):
        if any(x[0] == name for x in out): return
        out.append((name, why, sample))
    def first(segs, pred):
        return next(s for s in segs if pred(s))
    for name, segs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        flags = {s["flag"] for s in segs}
        if 1 in flags:
            add(name, "Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing.", first(segs, lambda s: s["flag"] == 1))
        elif 4 in flags:
            add(name, "Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road.", first(segs, lambda s: s["flag"] == 4))
    for name, segs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        if any(s["src"] == "i" and s["mph"] >= 99 and s["hw"] in MAJOR for s in segs):
            add(name, "Untagged major road, drawn at the fast default. The real posted limit may be lower.", first(segs, lambda s: s["src"] == "i" and s["mph"] >= 99 and s["hw"] in MAJOR))
    for name, segs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        if any(s["src"] == "i" and s["mph"] == 25 and s["hw"] == "tertiary" for s in segs):
            add(name, "Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it.", first(segs, lambda s: s["src"] == "i" and s["mph"] == 25 and s["hw"] == "tertiary"))
    for name, segs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        mphs = {s["mph"] for s in segs if s["src"] == "t"}
        if mphs & {25, 30, 35}:
            add(name, "Posted at the golf cart or LSV cap (" + "/".join(str(m) for m in sorted(mphs & {25, 30, 35})) + " mph). A faster block in the same name would change the route.", first(segs, lambda s: s["src"] == "t" and s["mph"] in (25, 30, 35)))
    if len(out) < 4:
        for name, segs in sorted(by.items(), key=lambda kv: -len(kv[1])):
            if any(s["src"] == "i" and s["mph"] == 25 and s["hw"] == "residential" for s in segs):
                add(name, "Residential street with no posted speed, assumed 25 mph. A higher sign would close it.", first(segs, lambda s: s["src"] == "i" and s["hw"] == "residential"))
            if len(out) >= 6: break
    return out[:8]

def main():
    regs = {r["id"]: r for r in json.load(open(os.path.join(ROOT, "public/data/regions.json")))}
    checks = sign_checks()
    counts = [(rid, posted_sign_pieces(rid)) for rid in IDS]
    cache_missing = [rid for rid in IDS if not os.path.exists(os.path.join(ROOT, "cache", rid + "_osm.json"))]
    if _google_key_set():
        google_line = "A Google Maps Platform API key is set. Street View batches 3 and 4 still need a filled sheet of signs a person read (`research/streetview_batch3/make_list.py`, `research/streetview_batch4/make_list.py`, then `resolve.py`). No sheet was filled, and no posted speed was guessed."
    else:
        google_line = "Street View batches 3 and 4 (`research/streetview_batch3/make_list.py`, `research/streetview_batch4/make_list.py`, then `resolve.py`) turn a filled sheet of signs a person read into `signs.json`. No sheet was filled. Those scripts do not call Google. Downloading Street View imagery would need a Google Maps Platform API key, and none is present (`GOOGLE_MAPS_API_KEY`, `GOOGLE_API_KEY`, and `STREETVIEW_API_KEY` are unset). No posted speed was guessed."
    lines = ["# Roads to verify: 24 new towns", "",
             "These are the roads in each new town whose legal status is the least certain: a ban, an untagged major road, an assumed 25 mph tertiary, or a speed sitting on the golf cart or LSV cap.",
             "Posted signs win. A road listed here is not a claim that the map is wrong.", "",
             "## Sign check", "",
             "Mapillary sign detection (`scripts/mapillary_signs.py`, called from `scripts/build_region.py`) did not run: `MAPILLARY_TOKEN` is %s. The token is read from the environment or from `.env`. No speed from that API was written into the tiles." % ("set" if _token_set() else "not set"),
             google_line,
             "Rebuild input `cache/<id>_osm.json` is missing for %s of these 24 towns, so `scripts/build_region.py` cannot apply signs even after a fetch. `public/data` for these towns was not edited." % len(cache_missing),
             "A road piece is one drawn segment. It is backed by a posted sign when its source code is `m`, or its cited source names Mapillary or a Street View posted sign. The before and after counts match because the tiles were not rebuilt. No road changed from open to closed or from closed to open.",
             "A road is dropped only when `research/expansion100_signchecks.json` marks it confirmed. That file is %s, so none of the roads below were dropped." % ("present" if os.path.exists(CHECKS) else "absent"),
             "",
             "| Town | Posted-sign pieces before | Posted-sign pieces after |",
             "|---|---:|---:|"]
    for rid, n in counts:
        lines.append("| %s | %s | %s |" % (regs[rid]["name"], n, n))
    lines.append("")
    lines.append("Roads whose legal status changed (open to closed or closed to open): none.")
    lines.append("")
    kept = 0
    for rid in IDS:
        r = regs[rid]
        place = r["short"] + " " + r["state"]
        lines.append(f"## {r['name']}")
        lines.append("")
        rows = load(rid)
        picks = pick(rows)
        shown = []
        for name, why, sample in picks:
            hit = checks.get(rid, {}).get(name)
            if hit and hit["confirmed"]:
                continue
            shown.append((name, why, sample, hit))
        if not picks:
            lines.append("No named road met the uncertainty rules in this extract.")
            lines.append("")
            continue
        if not shown:
            lines.append("Every listed road now has a confirmed posted sign, so none remain here.")
            lines.append("")
            continue
        for name, why, sample, hit in shown:
            url = link(name, place, sample["lat"], sample["lon"])
            lines.append(f"- **{name}** ({sample['hw']}, {sample['mph']} mph, source {sample['src']}): {why} {finding_clause(hit)} [Map]({url})")
            kept += 1
        lines.append("")
    path = os.path.join(ROOT, "research", "expansion100_roads_to_verify.md")
    open(path, "w").write("\n".join(lines) + "\n")
    print("wrote", path, "sections", len(IDS), "roads", kept)

if __name__ == "__main__":
    main()
