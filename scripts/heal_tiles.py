#!/usr/bin/env python3
"""Apply the same-road island rule (scripts/islands.py heal) to an already-built region, for regions whose OSM cache isn't on
this machine (the builders run the same function on every build, so a rebuild gives the same result).
usage: heal_tiles.py <region> [...]"""
import json, os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import islands as ISL
for rid in sys.argv[1:]:
    d = os.path.join(HERE, "..", "public", "data", rid); ix = json.load(open(os.path.join(d, "index.json")))
    tiles = {f: json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "tiles", "*.json")))}
    segs = [s for t in tiles.values() for s in t]   # same list objects: heal edits them in place
    ch = ISL.heal(segs, ix["names"], ix["sources"])
    for c in ch: print(rid, "healed", c)
    if not ch: print(rid, "nothing to heal"); continue
    st = ix["meta"].setdefault("stats", {})
    st["same_road_gap"] = st.get("same_road_gap", 0) + sum(c["code"] == "n" for c in ch); st["same_road_disagree"] = st.get("same_road_disagree", 0) + sum(c["code"] == "q" for c in ch)
    for f, t in tiles.items(): open(f, "w").write(json.dumps(t, separators=(",", ":")))
    open(os.path.join(d, "index.json"), "w").write(json.dumps(ix, separators=(",", ":")))
