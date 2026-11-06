#!/usr/bin/env python3
"""Write research/expansion100_roads_to_verify.md from the built tiles of the 24 new regions.
Picks named roads whose legal status is the least certain: a ban, an inferred fast class,
an inferred 25 mph tertiary, or a speed sitting on the golf cart or LSV cap."""
import glob, json, os, collections
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
IDS = ["fairhope", "ocracoke", "dadecity", "mountdora", "pinehurst", "beaufort", "portroyal",
       "georgetown", "horseshoebay", "surfside", "colonialbeach", "flaglerbeach", "oriental",
       "celina", "capecharles", "sunlakes", "morrobay", "pismo", "howey", "apalachicola",
       "cedarkey", "islamorada", "keylargo", "crystalriver"]
MAJOR = {"primary", "secondary", "tertiary", "trunk"}

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
    lines = ["# Roads to verify: 24 new towns", "",
             "These are the roads in each new town whose legal status is the least certain: a ban, an untagged major road, an assumed 25 mph tertiary, or a speed sitting on the golf cart or LSV cap.",
             "Posted signs win. A road listed here is not a claim that the map is wrong.", ""]
    for rid in IDS:
        r = regs[rid]
        place = r["short"] + " " + r["state"]
        lines.append(f"## {r['name']}")
        lines.append("")
        rows = load(rid)
        picks = pick(rows)
        if not picks:
            lines.append("No named road met the uncertainty rules in this extract.")
            lines.append("")
            continue
        for name, why, sample in picks:
            url = link(name, place, sample["lat"], sample["lon"])
            lines.append(f"- **{name}** ({sample['hw']}, {sample['mph']} mph, source {sample['src']}): {why} [Map]({url})")
        lines.append("")
    path = os.path.join(ROOT, "research", "expansion100_roads_to_verify.md")
    open(path, "w").write("\n".join(lines) + "\n")
    print("wrote", path, "sections", len(IDS))

if __name__ == "__main__":
    main()
