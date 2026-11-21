#!/usr/bin/env python3
"""Guard for the conservative posted-limit rule (scripts/overrides.py, CVC 22357): a lower local limit only counts once its signs
are up. Data: research/posted_limits.json (sign-posted limits that differ from the limit the map uses).

Fails when:
  1. a stretch whose sign-posted limit is above the region's LSV cap, with new signs not confirmed, has any segment shown
     LSV-legal (by public/roadrule.js), whatever caution, note or override covers it. Segments are found by geometry
     (osm_name + midpoint in bbox) and by the stretch's label, so a relabelled override is still caught;
  2. a CAU caution in public/app.js has no posted_limits entry (every caution must declare the posted limit it is about);
  3. an entry says new_signs_confirmed without signs_evidence, or is missing a field;
  4. a BLK note in public/app.js matches no segment (stale after a block is lifted: delete it).

Usage: python3 scripts/check_posted_limits.py [--root DIR] [--limits FILE]
  --root: the checkout to check (default: this repo). --limits: default <root>/research/posted_limits.json."""
import argparse, glob, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = ("id", "region", "road", "osm_name", "stretch", "label", "bbox", "posted_mph", "posted_evidence", "lowered_to_mph",
          "map_uses_posted", "new_signs_confirmed", "signs_evidence")
NODE = r"""const R=require(process.argv[1]),fs=require('fs');const q=JSON.parse(fs.readFileSync(0,'utf8'));
const rules=JSON.parse(fs.readFileSync(q.rules)),reg=JSON.parse(fs.readFileSync(q.regions)).find(r=>r.id===q.region);
const L=R.ruleFor(rules,reg,'lsv');process.stdout.write(JSON.stringify({max:L.max_posted,cls:q.segs.map(s=>R.cls(s,L))}))"""


def lsv_cls(root, region, segs):
    pub = os.path.join(root, "public")
    q = {"rules": os.path.join(pub, "data", "rules.json"), "regions": os.path.join(pub, "data", "regions.json"), "region": region, "segs": segs}
    out = subprocess.run(["node", "-e", NODE, os.path.join(pub, "roadrule.js")], input=json.dumps(q), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def js_list(js, name):
    i = js.find(f"const {name}=[")
    if i < 0:
        return []
    j = js.index("];", i)
    return re.findall(r"\{src:'([^']+)'", js[i:j])


def check(root, limits_path):
    fails, oks = [], []
    stretches = json.load(open(limits_path))["stretches"]
    js = open(os.path.join(root, "public", "app.js"), encoding="utf-8").read()
    data = {}
    for e in stretches:
        miss = [f for f in FIELDS if f not in e]
        if miss:
            fails.append(f"{e.get('id')}: missing field(s) {miss}"); continue
        if e["new_signs_confirmed"] and not e["signs_evidence"]:
            fails.append(f"{e['id']}: new_signs_confirmed needs signs_evidence (a dated photo or notice of the new signs)")
        if e["posted_mph"] is None and not e["posted_evidence"]:
            fails.append(f"{e['id']}: posted_mph null needs posted_evidence saying why")
        reg = e["region"]
        if reg not in data:
            d = os.path.join(root, "public", "data", reg)
            idx = json.load(open(os.path.join(d, "index.json")))
            segs = [s for f in sorted(glob.glob(os.path.join(d, "tiles", "*.json"))) for s in json.load(open(f))]
            data[reg] = (idx, segs)
        idx, segs = data[reg]
        lab = lambda s: idx["sources"][s[8]][1] if len(s) > 8 and isinstance(s[8], int) and s[8] < len(idx["sources"]) else ""
        S, W, N, E = e["bbox"]
        hit = []
        for s in segs:
            m = s[7][len(s[7]) // 2]
            if (idx["names"][s[0]] == e["osm_name"] and S <= m[1] <= N and W <= m[0] <= E) or e["label"] in lab(s):
                hit.append(s)
        e["_hits"] = len(hit)
        if not hit:
            fails.append(f"{e['id']}: no segments found (osm_name {e['osm_name']!r}, bbox {e['bbox']}, label {e['label']!r})"); continue
        r = lsv_cls(root, reg, hit)
        if e["posted_mph"] is not None and not e["new_signs_confirmed"] and e["posted_mph"] > r["max"]:
            legal = [s for s, c in zip(hit, r["cls"]) if c != 3]
            if legal:
                sp = sorted({s[2] for s in legal})
                fails.append(f"{e['id']}: signs posted {e['posted_mph']} mph (new signs not confirmed) but {len(legal)} of {len(hit)} segments "
                             f"shown LSV-legal at {sp} mph (LSV cap {r['max']}). {e['road']} {e['stretch']}. Labels: {sorted({lab(s) for s in legal})[:2]}")
            else:
                oks.append(f"{e['id']}: posted {e['posted_mph']} > {r['max']}, all {len(hit)} segments not LSV-legal")
        else:
            oks.append(f"{e['id']}: posted {e['posted_mph']}, {len(hit)} segments (no block needed)")
    labels = [e["label"] for e in stretches]
    for src in js_list(js, "CAU"):
        if not any(l in src or src in l for l in labels):
            fails.append(f"CAU caution {src!r} has no research/posted_limits.json entry (declare its sign-posted limit)")
        else:
            oks.append(f"CAU {src[:60]!r} declared")
    if js_list(js, "BLK"):
        idx, segs = data.get("sd") or (None, [])
        labs = {idx["sources"][s[8]][1] for s in segs if len(s) > 8 and isinstance(s[8], int)} if idx else set()
        for src in js_list(js, "BLK"):
            if not any(src in l for l in labs):
                fails.append(f"BLK note {src!r} matches no segment: the block was lifted, delete this line from public/app.js")
            else:
                oks.append(f"BLK {src[:60]!r} matches data")
    return fails, oks


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(HERE, ".."))
    ap.add_argument("--limits")
    a = ap.parse_args(argv)
    fails, oks = check(a.root, a.limits or os.path.join(a.root, "research", "posted_limits.json"))
    for o in oks:
        print("PASS", o)
    for f in fails:
        print("FAIL", f)
    print("RESULT", "ALL PASS" if not fails else f"{len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
