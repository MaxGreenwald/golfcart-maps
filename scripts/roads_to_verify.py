#!/usr/bin/env python3
"""Write research/expansion100_roads_to_verify.md for the 24 new towns.

The road list is the uncertain named roads on the pre-sign build (git 62e364b,
same road lines as master d2e58d3). A road is dropped only when every current
piece of that name is backed by a posted sign and none carries an explicit ban.
Mapillary and Street View are not called from here.
"""
import collections, json, os, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
IDS = ["fairhope", "ocracoke", "dadecity", "mountdora", "pinehurst", "beaufort", "portroyal",
       "georgetown", "horseshoebay", "surfside", "colonialbeach", "flaglerbeach", "oriental",
       "celina", "capecharles", "sunlakes", "morrobay", "pismo", "howey", "apalachicola",
       "cedarkey", "islamorada", "keylargo", "crystalriver"]
MAJOR = {"primary", "secondary", "tertiary", "trunk"}
BEFORE = "62e364b7a80e2dee885dda33bb45c6107d87b585"
REJECTIONS = os.path.join(ROOT, "research", "expansion100_sign_rejections.json")

def load_tiles(idx, reader):
    segs = []
    for t in idx["meta"]["tiles"]:
        segs += reader(t)
    return segs

def load_current(rid):
    idx = json.load(open(os.path.join(ROOT, "public/data", rid, "index.json")))
    def reader(t):
        return json.load(open(os.path.join(ROOT, "public/data", rid, "tiles", t + ".json")))
    return idx, load_tiles(idx, reader)

def load_before(rid):
    def show(path):
        return json.loads(subprocess.check_output(["git", "show", "%s:%s" % (BEFORE, path)]))
    idx = show("public/data/%s/index.json" % rid)
    def reader(t):
        return show("public/data/%s/tiles/%s.json" % (rid, t))
    return idx, load_tiles(idx, reader)

def rows_of(idx, segs):
    names = idx["names"]
    rows = []
    for s in segs:
        if not names[s[0]]: continue
        mid = s[7][len(s[7]) // 2]
        rows.append({"name": names[s[0]], "hw": s[1].replace("_link", ""), "mph": s[2], "src": s[3],
                     "flag": s[9] if len(s) > 9 else 0, "lat": mid[1], "lon": mid[0], "n": len(s[7])})
    return rows

def is_sign_backed(seg, sources):
    """A drawn piece whose speed comes from Mapillary or a Street View posted sign."""
    if seg[3] in ("m", "s"):
        return True
    if len(seg) > 8 and isinstance(seg[8], int) and 0 <= seg[8] < len(sources or []):
        lab = sources[seg[8]][1].lower()
        if "mapillary" in lab or "posted sign" in lab or "street view" in lab:
            return True
    return False

def posted_sign_pieces(rid):
    idx, segs = load_current(rid)
    return sum(1 for s in segs if is_sign_backed(s, idx.get("sources") or []))

def road_confirmed(pieces):
    """True when every piece has sign evidence and none is an explicit ban (flag 1 or 4)."""
    if not pieces:
        return False
    return all(p["sign"] for p in pieces) and not any(p["flag"] in (1, 4) for p in pieces)

def finding_clause(mphs, sources):
    if not mphs:
        return "Posted speed seen: not read. Source: none."
    speeds = "/".join(str(m) for m in mphs)
    src = "; ".join(sources) if sources else "none"
    return "Posted speed seen: %s mph. Source: %s." % (speeds, src)

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

def rule_for(rules, reg, veh):
    """Same merge as public/roadrule.js ruleFor. lenient crossings are off."""
    st = (rules or {}).get(reg.get("state") or "") or (rules or {}).get("CA") or {}
    rr = reg.get("rule") or {}
    flat = {k: v for k, v in rr.items() if k not in ("golf_cart", "lsv")}
    base = dict(st.get(veh) or {"not_street_legal": True, "unconfirmed": True, "max_posted": 0})
    r = {"cross": True}
    r.update(base)
    r.update(flat)
    r.update(rr.get(veh) or {})
    r["veh"] = veh
    if r.get("not_street_legal"):
        r["max_posted"] = 0
    return r

def segment_open(seg, rule):
    if seg[3] == "c":
        return True
    if rule.get("not_street_legal"):
        return False
    flag = seg[9] if len(seg) > 9 else 0
    hw = seg[1]
    if flag == 1 and hw.split("_")[0] in ("motorway", "trunk", "primary"):
        return False
    if flag == 4 and rule.get("veh") == "golf_cart":
        return False
    if seg[2] is None or seg[2] > rule.get("max_posted", 0):
        return False
    assume = rule.get("assume") or []
    designated = seg[3] in ("c", "d") or (hw in assume and seg[2] is not None and seg[2] <= rule.get("max_posted", 0))
    if rule.get("designated_only") and not designated:
        return False
    return True

def geom_key(idx, seg):
    return (idx["names"][seg[0]], seg[1], tuple((round(p[0], 5), round(p[1], 5)) for p in seg[7]))

def source_text(idx, seg):
    if len(seg) > 8 and isinstance(seg[8], int) and 0 <= seg[8] < len(idx.get("sources") or []):
        return idx["sources"][seg[8]]
    return None

def legal_changes(rid, reg, rules, before, after):
    bi, bs = before
    ai, as_ = after
    bmap = {geom_key(bi, s): s for s in bs}
    amap = {geom_key(ai, s): s for s in as_}
    grouped = collections.defaultdict(list)
    for k in set(bmap) & set(amap):
        old, new = bmap[k], amap[k]
        for veh in ("golf_cart", "lsv"):
            ro, rn = rule_for(rules, reg, veh), rule_for(rules, reg, veh)
            if segment_open(old, ro) == segment_open(new, rn):
                continue
            change = "closed to open" if segment_open(new, rn) else "open to closed"
            so = source_text(ai, new)
            grouped[(ai["names"][new[0]], veh, change, old[2], new[2])].append(so[0] if so else "")
    out = []
    for (road, veh, change, old_mph, new_mph), urls in sorted(grouped.items()):
        out.append({"road": road, "vehicle": veh, "change": change, "old_mph": old_mph, "new_mph": new_mph,
                    "pieces": len(urls), "sources": sorted({u for u in urls if u})})
    return out

def main():
    regs = {r["id"]: r for r in json.load(open(os.path.join(ROOT, "public/data/regions.json")))}
    rules = json.load(open(os.path.join(ROOT, "public/data/rules.json")))
    rejections = json.load(open(REJECTIONS)) if os.path.exists(REJECTIONS) else []
    lines = ["# Roads to verify: 24 new towns", "",
             "These are the roads in each new town whose legal status was the least certain before the Mapillary pass: a ban, an untagged major road, an assumed 25 mph tertiary, or a speed sitting on the golf cart or LSV cap.",
             "Posted signs win. A road listed here is not a claim that the map is wrong.", "",
             "## Sign check", "",
             "Posted speeds come from the Mapillary detections in the cached run of `scripts/build_region.py` (`scripts/mapillary_signs.py`). They were copied onto the road lines already in master d2e58d3. A different OSM extract would have added 64 pieces and removed 183 across Fairhope, Dade City, Mount Dora, Pinehurst, Howey-in-the-Hills, and Crystal River. Those line changes were not applied.",
             "A 15 mph detection on a piece posted 45 mph was not applied. That pattern fits a school-zone or advisory sign, and it is not enough to open the road. See `research/expansion100_sign_rejections.json`.",
             "Street View batches 3 and 4 still need a person to read a sign photo. No Street View sheet was filled, and no posted speed was guessed from an unread image.",
             "A road piece is one drawn segment. It is backed by a posted sign when its source code is `m` (Mapillary) or `s` (Street View), or its cited source names Mapillary or a Street View posted sign. Before counts are the pre-sign build (git 62e364b). A listed road is dropped only when every current piece of that name has that evidence and none has an explicit ban (flag 1 or 4).",
             "",
             "| Town | Posted-sign pieces before | Posted-sign pieces after |",
             "|---|---:|---:|"]
    changes = []
    kept = 0
    resolved = []
    sections = []
    for rid in IDS:
        reg = regs[rid]
        bi, bs = load_before(rid)
        ai, as_ = load_current(rid)
        before_n = sum(1 for s in bs if is_sign_backed(s, bi.get("sources") or []))
        after_n = sum(1 for s in as_ if is_sign_backed(s, ai.get("sources") or []))
        lines.append("| %s | %s | %s |" % (reg["name"], before_n, after_n))
        for c in legal_changes(rid, reg, rules, (bi, bs), (ai, as_)):
            changes.append(dict(region=rid, town=reg["name"], **c))
        by = collections.defaultdict(list)
        for s in as_:
            if not ai["names"][s[0]]: continue
            so = source_text(ai, s)
            by[ai["names"][s[0]]].append({"sign": is_sign_backed(s, ai.get("sources") or []),
                                          "flag": s[9] if len(s) > 9 else 0, "mph": s[2],
                                          "source": so[0] if so else ""})
        place = reg["short"] + " " + reg["state"]
        body = ["## %s" % reg["name"], ""]
        shown = 0
        for name, why, sample in pick(rows_of(bi, bs)):
            pieces = by.get(name, [])
            if road_confirmed(pieces):
                mphs = sorted({p["mph"] for p in pieces})
                resolved.append((reg["name"], name, "/".join(str(m) for m in mphs), len(pieces)))
                continue
            mphs = sorted({p["mph"] for p in pieces if p["sign"]})
            srcs = sorted({p["source"] for p in pieces if p["sign"] and p["source"]})
            url = link(name, place, sample["lat"], sample["lon"])
            body.append("- **%s** (%s, %s mph, source %s): %s %s Sign coverage: %s/%s current pieces. [Map](%s)" % (
                name, sample["hw"], sample["mph"], sample["src"], why, finding_clause(mphs, srcs),
                sum(1 for p in pieces if p["sign"]), len(pieces), url))
            shown += 1
            kept += 1
        if not shown:
            body.append("Every original uncertain road in this town now has complete sign coverage and no explicit ban.")
        body.append("")
        sections.append("\n".join(body))
    lines += ["", "## Roads whose legal status changed", "",
              "Open and closed follow `public/roadrule.js` for each vehicle, on pieces whose line did not move. This is before the route-level 75-foot faster-road waiver. 99 is an unknown or ban sentinel, not a measured speed.",
              "",
              "| Town | Road | Vehicle | Change | Old speed | New speed | Pieces | Source |",
              "|---|---|---|---|---:|---:|---:|---|"]
    if not changes:
        lines.append("| (none) | | | | | | | |")
    for c in changes:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            c["town"], c["road"] or "(unnamed)", c["vehicle"], c["change"], c["old_mph"], c["new_mph"], c["pieces"],
            "; ".join(c["sources"])))
    lines += ["", "## Readings that were not applied", "",
              "These Mapillary speeds would have opened a road posted 45 mph. They were left at the previous speed.",
              "",
              "| Town | Road | Pieces | Was | Detected | Why |",
              "|---|---|---:|---:|---:|---|"]
    for r in rejections:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (regs[r["region"]]["name"], r["road"], r["n"], r["old"], r["new"], r["reason"]))
    lines += ["", "## Resolved original rows", "",
              "A row is resolved only when every current piece of that road name has sign evidence and no explicit ban remains.",
              "",
              "| Town | Road | Detected mph | Pieces |",
              "|---|---|---|---:|"]
    if not resolved:
        lines.append("| (none) | | | |")
    for town, name, mph, n in resolved:
        lines.append("| %s | %s | %s | %s |" % (town, name, mph, n))
    lines.append("")
    lines.extend(sections)
    path = os.path.join(ROOT, "research", "expansion100_roads_to_verify.md")
    open(path, "w").write("\n".join(lines) + "\n")
    print("wrote", path, "kept", kept, "resolved", len(resolved), "changes", len(changes))

if __name__ == "__main__":
    main()
