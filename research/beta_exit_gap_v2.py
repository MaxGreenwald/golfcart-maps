#!/usr/bin/env python3
"""Beta-exit gap v2 (analysis only; changes no data or source codes).
Usage: beta_exit_gap_v2.py [DATA_ROOT]  (DATA_ROOT has public/data and cache/; default: repo root)
Counts by MILES on important roads (primary/secondary/tertiary + _link; trunk only when posted <=35).
Sourced = v | m | d-with-source (unchanged from v1). Adds:
  I  neighbour inference: an unsourced same-name run bounded on >=2 sides by sourced segments that all
     post the same mph, same class, none banned, run <= 1.5 mi, and no ban inside. Never credited if it
     would make the road more permissive than today (red->green / lifts ban): those are only counted as 'flagged'.
  T  trusted OSM (candidate rules measured against v/m segments; see report).
  Corridors: remaining unsourced same-name connected runs, split where the current mph or class changes.
"""
import json, glob, math, os, sys, re, collections
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..")
IMP = {"primary", "secondary", "tertiary"}; MI = 0.621371; CORR_MIN = 0.25; RUN_MAX = 1.5; BAR = 0.70
BIG = ["sd", "ocoast", "suncity", "coachella", "villages", "myrtle", "naples"]
def km(g): return sum(math.hypot((g[i][1]-g[i-1][1])*110.574, (g[i][0]-g[i-1][0])*111.32*math.cos(math.radians(g[i][1]))) for i in range(1, len(g)))
def mph_of(v):
    m = re.match(r"\s*(\d+)\s*(mph)?", v or ""); 
    if not m: return None
    n = int(m.group(1)); return n if m.group(2) or n <= 85 else round(n*MI)
def tier(t):
    src = (t.get("source:maxspeed") or "").lower(); typ = (t.get("maxspeed:type") or "").lower(); ms = t.get("maxspeed", "")
    if not ms: return "none"
    if re.match(r"^[a-z]{2}(-[a-z]{2})?:", ms.lower()) or re.match(r"^[a-z]{2}(-[a-z]{2})?:", src) or re.match(r"^[a-z]{2}(-[a-z]{2})?:", typ) \
       or "vehicle code" in src or "motor vehicle" in src: return "implied"
    if "sign" in src or "survey" in src or "image" in src or "streetside" in src or "local_knowledge" in src or typ == "sign": return "sign_survey"
    if "fdot" in src or "dot" in src: return "dot_gis"
    return "explicit_nosource"
def osm_files(r):
    return sorted(glob.glob(f"{ROOT}/cache/v2_tile*.json") + glob.glob(f"{ROOT}/cache/tile[0-9]*.json")) if r == "sd" else [f"{ROOT}/cache/{r}_osm.json"]
SIG = collections.Counter(); AGREE = collections.defaultdict(lambda: [0, 0]); out = []; corr_all = {}
for d in sorted(glob.glob(f"{ROOT}/public/data/*/index.json")):
    r = d.split("/")[-2]; names = json.load(open(d))["names"]
    # --- OSM tags by point
    pt = collections.defaultdict(set); tags = {}; have_osm = False
    for f in osm_files(r):
        if not os.path.exists(f): continue
        have_osm = True
        for el in json.load(open(f))["elements"]:
            if el.get("type") != "way" or "highway" not in el.get("tags", {}): continue
            t = el["tags"]; tags[el["id"]] = t
            for k in ("version", "timestamp"): SIG[k] += k in el
            for k in ("source:maxspeed", "maxspeed:type"): SIG[k] += k in t
            for p in el.get("geometry") or []: pt[(round(p["lon"], 5), round(p["lat"], 5))].add(el["id"])
    segs = {}
    for f in glob.glob(f"{ROOT}/public/data/{r}/tiles/*.json"):
        for s in json.load(open(f)):
            hw = s[1].replace("_link", "")
            if not (hw in IMP or (hw == "trunk" and s[2] <= 35)): continue
            k = (min(s[5], s[6]), max(s[5], s[6]))
            if k in segs: continue
            src = len(s) > 8 and s[8] >= 0
            ok = s[3] in ("v", "m") or (s[3] == "d" and src)
            ws = pt.get(tuple(s[7][0]), set()) & pt.get(tuple(s[7][-1]), set())
            w = next((x for x in ws if (tags[x].get("name") or tags[x].get("ref") or "") == names[s[0]]), next(iter(ws), None))
            t = tags.get(w, {}) if w else {}
            segs[k] = dict(nm=names[s[0]], hw=s[1], mph=s[2], code=s[3], ban=s[4] == 1, a=s[5], b=s[6], L=km(s[7])*MI, ok=ok,
                           tier=(tier(t) if w else ("unmatched" if have_osm else "no_extract")), osm=mph_of(t.get("maxspeed")) if w else None)
    S = list(segs.values()); L = sum(x["L"] for x in S) or 1e-9
    byn = collections.defaultdict(list)
    for x in S: byn[(x["a"], x["nm"])].append(x); byn[(x["b"], x["nm"])].append(x)
    def nbrs(x): return [y for n in (x["a"], x["b"]) for y in byn[(n, x["nm"])] if y is not x]
    # --- agreement of OSM tiers vs real sources (v/m only: independent of OSM)
    for x in S:
        if x["code"] in ("v", "m") and x["osm"] is not None and x["mph"] < 99 and not x["ban"]:   # 99 = ban sentinel, not a posted speed
            AGREE[x["tier"]][0] += x["osm"] == x["mph"]; AGREE[x["tier"]][1] += 1
            AGREE[x["tier"] + " vs " + x["code"]][0] += x["osm"] == x["mph"]; AGREE[x["tier"] + " vs " + x["code"]][1] += 1
            nb = [y["mph"] for y in nbrs(x) if y["code"] in ("v", "m") and y["mph"] < 99]
            if nb and x["tier"] != "implied":
                key = "explicit+neighbour_agrees" if x["osm"] in nb else "explicit+neighbour_disagrees"
                AGREE[key][0] += x["osm"] == x["mph"]; AGREE[key][1] += 1
    # --- inference: unsourced same-name components bounded by sourced segs of one speed
    inf = set(); flagged = 0; seen = set()
    for x in S:
        if x["ok"] or id(x) in seen or not x["nm"]: continue
        comp, st, bound = [], [x], []
        seen.add(id(x))
        while st:
            c = st.pop(); comp.append(c)
            for y in nbrs(c):
                if y["ok"]: bound.append(y)
                elif id(y) not in seen: seen.add(id(y)); st.append(y)
        bnodes = {n for y in bound for n in (y["a"], y["b"])}
        sp = {y["mph"] for y in bound}; sp = sp if 99 not in sp else {0, 1}; cls = {y["hw"] for y in bound} | {c["hw"] for c in comp}
        if len({id(y) for y in bound}) >= 2 and len(sp) == 1 and len(cls) == 1 and not any(y["ban"] for y in bound + comp) \
           and sum(c["L"] for c in comp) <= RUN_MAX:
            v = sp.pop()
            for c in comp:
                if v < c["mph"] or c["mph"] > 35 >= v: flagged += 1; c["flag"] = v      # more permissive than today -> needs a photo
                else: inf.add(id(c)); c["inf"] = v
    # --- trusted OSM candidates
    def trusted(x, rule):
        if x["osm"] is None or x["tier"] in ("implied", "none", "unmatched", "no_extract"): return False
        if rule == "sign": return x["tier"] == "sign_survey"
        if rule == "nbr": return (x["osm"] in [y["mph"] for y in nbrs(x) if y["ok"] and y["mph"] < 99])
        return False
    Ls = sum(x["L"] for x in S if x["ok"]); Li = Ls + sum(x["L"] for x in S if id(x) in inf)
    row = dict(r=r, L=L, s=Ls/L, si=Li/L, flagged=flagged, have=have_osm)
    for rule in ("none", "sign", "nbr"):
        cov = lambda x: x["ok"] or id(x) in inf or trusted(x, rule)
        row["st_" + rule] = sum(x["L"] for x in S if cov(x))/L
        # corridors over uncovered segments, split on mph/class change
        cs, sn = [], set()
        for x in S:
            if cov(x) or id(x) in sn: continue
            comp, st = [], [x]; sn.add(id(x))
            while st:
                c = st.pop(); comp.append(c)
                for y in nbrs(c) if c["nm"] else []:
                    if not cov(y) and id(y) not in sn and y["mph"] == c["mph"] and y["hw"].replace("_link","") == c["hw"].replace("_link",""):
                        sn.add(id(y)); st.append(y)
            cs.append((sum(c["L"] for c in comp), comp[0]["nm"] or "(unnamed)", comp[0]["mph"], comp[0]["hw"], collections.Counter(c["tier"] for c in comp).most_common(1)[0][0]))
        cs.sort(reverse=True); need = max(0.0, BAR*L - row["st_" + rule]*L); acc = 0; n = 0
        for c in cs:
            if acc >= need or c[0] < CORR_MIN: break
            acc += c[0]; n += 1
        row["c_" + rule] = (n, acc, need, acc + 1e-9 >= need, len([c for c in cs if c[0] >= CORR_MIN]), sum(c[0] for c in cs if c[0] >= CORR_MIN))
        if rule in ("none", "nbr"): corr_all[(r, rule)] = cs
    gap = collections.Counter()
    for x in S:
        if not (x["ok"] or id(x) in inf): gap[x["tier"]] += x["L"]
    row["gap"] = gap; out.append(row)
json.dump(dict(rows=[{**r, "gap": dict(r["gap"])} for r in out], agree={k: v for k, v in AGREE.items()}, signals=dict(SIG),
               corridors={f"{k[0]}|{k[1]}": v[:15] for k, v in corr_all.items() if k[0] in BIG}), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "beta_exit_gap_v2_2026-10-22.json"), "w"))
print("signals present (count of ways carrying them):", dict(SIG))
print("\n| Tier / rule | Agree | n | % |\n|---|---:|---:|---:|")
for k, (a, n) in sorted(AGREE.items(), key=lambda kv: -kv[1][1]): print(f"| {k} | {a:,} | {n:,} | {100*a/max(n,1):.1f}% |")
print("\n| Region | Important mi | v1 % mi sourced | + inference | + inference + trusted OSM (neighbour-agree rule) | Flagged inferences | Corridors >=0.25 mi to 70% (no OSM trust) | Mi | Corridors to 70% (with trusted OSM) | Mi |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
def cc(c): return f"{c[0]:,}{'' if c[3] else '*'}"
for x in sorted(out, key=lambda x: -x["si"]):
    a, b = x["c_none"], x["c_nbr"]
    print(f"| {x['r']} | {x['L']:,.1f} | {100*x['s']:.1f}% | {100*x['si']:.1f}% | {100*x['st_nbr']:.1f}%{'' if x['have'] else ' (no extract)'} | {x['flagged']} | {cc(a)} | {a[1]:,.1f} | {cc(b)} | {b[1]:,.1f} |")
T = lambda k: sum(x[k]*x["L"] for x in out)/sum(x["L"] for x in out)
print(f"| **All {len(out)}** | {sum(x['L'] for x in out):,.0f} | {100*T('s'):.1f}% | {100*T('si'):.1f}% | {100*T('st_nbr'):.1f}% | {sum(x['flagged'] for x in out)} | {sum(x['c_none'][0] for x in out):,} | {sum(x['c_none'][1] for x in out):,.0f} | {sum(x['c_nbr'][0] for x in out):,} | {sum(x['c_nbr'][1] for x in out):,.0f} |")
print("\n'*' = corridors >=0.25 mi alone can't reach 70%; the rest is short pieces/links.")
print("\nsign/survey-only rule coverage (rejected):", {x["r"]: round(100*x["st_sign"], 1) for x in out if x["r"] in BIG})
print("\nRemaining gap miles by OSM tier (after inference):")
for x in out:
    if x["r"] in BIG: print(x["r"], {k: round(v, 1) for k, v in x["gap"].most_common()})
for r in BIG:
    for rule in ("none", "nbr"):
        print(f"\n{r} top corridors ({rule}):", "; ".join(f"{c[1]} {c[0]:.2f} mi @{c[2] if c[2] < 99 else 'unknown'} [{c[4]}]" for c in corr_all[(r, rule)][:10]))
