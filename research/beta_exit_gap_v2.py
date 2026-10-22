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
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CACHE = os.environ.get("CACHE", os.path.join(ROOT, "cache"))   # OSM extracts (gitignored); only for the OSM-confidence columns
IMP = {"primary", "secondary", "tertiary"}; MI = 0.621371; CORR_MIN = 0.25; RUN_MAX = 1.5; BAR = 0.70
HERE = os.path.dirname(os.path.abspath(__file__))
ACCESS = json.load(open(os.path.join(HERE, "access_sources.json")))["regions"]     # rule 2: local access source per region
GRIDS = json.load(open(os.path.join(HERE, "beta_grids.json")))["regions"]          # rule 4: resort/town-centre grids
REPORTS = json.load(open(os.path.join(HERE, "road_reports.json")))["reports"]      # rule 5: shop/user reports
GRID_HW = {"residential", "unclassified", "living_street"}
COUNTY = re.compile(r"\b(CR|County (Road|Highway|Hwy|Rd))\b|^C-?\d", re.I)
def in_bb(p, bb): return bb[0] <= p[1] <= bb[2] and bb[1] <= p[0] <= bb[3]
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
    return sorted(glob.glob(f"{CACHE}/v2_tile*.json") + glob.glob(f"{CACHE}/tile[0-9]*.json")) if r == "sd" else [f"{CACHE}/{r}_osm.json"]
CHECK = {}; DUMPED = {}; SIG = collections.Counter(); AGREE = collections.defaultdict(lambda: [0, 0]); out = []; corr_all = {}
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
    segs = {}; nodenames = collections.defaultdict(set)
    for f in glob.glob(f"{ROOT}/public/data/{r}/tiles/*.json"):
        for s in json.load(open(f)):
            nodenames[s[5]].add(names[s[0]]); nodenames[s[6]].add(names[s[0]])
            hw = s[1].replace("_link", "")
            mid = s[7][len(s[7])//2]
            grid = next((gname for gname, bb in GRIDS.get(r, {}).items() if in_bb(mid, bb)), None) if s[1] in GRID_HW and r in ACCESS else None
            if not (hw in IMP or (hw == "trunk" and s[2] <= 35) or grid): continue
            k = (min(s[5], s[6]), max(s[5], s[6]))
            if k in segs: continue
            src = len(s) > 8 and s[8] >= 0
            ok = s[3] in ("v", "m", "o") or (s[3] == "d" and src)   # o = trusted OSM (scripts/trusted_osm.py, Max OK 2026-10-22)
            ws = pt.get(tuple(s[7][0]), set()) & pt.get(tuple(s[7][-1]), set())
            w = next((x for x in ws if (tags[x].get("name") or tags[x].get("ref") or "") == names[s[0]]), next(iter(ws), None))
            t = tags.get(w, {}) if w else {}
            segs[k] = dict(nm=names[s[0]], hw=s[1], mph=s[2], code=s[3], ban=(len(s) > 9 and s[9] == 1) or (s[3] == "v" and s[2] >= 99), grid=grid, a=s[5], b=s[6], L=km(s[7])*MI, ok=ok, src=len(s) > 8 and s[8] >= 0,
                           tier=(tier(t) if w else ("unmatched" if have_osm else "no_extract")), osm=mph_of(t.get("maxspeed")) if w else None, way=w, g=s[7])
    S = list(segs.values())
    BANS = [x for x in S if x["ban"]]   # rule 3: banned stretches are scored on their own and are not in the 70%
    L = sum(x["L"] for x in S if not x["ban"]) or 1e-9
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
    Ls = sum(x["L"] for x in S if x["ok"] and not x["ban"]); Li = Ls + sum(x["L"] for x in S if id(x) in inf and not x["ban"])
    row = dict(r=r, L=L, s=Ls/L, si=Li/L, flagged=flagged, have=have_osm)
    for rule in ("none", "sign", "nbr"):
        cov = lambda x: x["ban"] or x["ok"] or id(x) in inf or trusted(x, rule)   # bans never become corridors (scored apart)
        row["st_" + rule] = sum(x["L"] for x in S if cov(x) and not x["ban"])/L
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
            cs.append((sum(c["L"] for c in comp), comp[0]["nm"] or "(unnamed)", comp[0]["mph"], comp[0]["hw"], collections.Counter(c["tier"] for c in comp).most_common(1)[0][0], comp))
        # rule 1, conflict-first: a corridor whose road is posted differently right next to it by a real source
        cs = [c + (any(y["ok"] and not y["ban"] and y["mph"] < 99 and y["mph"] != c[2] for z in c[5] for y in nbrs(z)),) for c in cs]
        cs.sort(key=lambda c: -c[0]); need = max(0.0, BAR*L - row["st_" + rule]*L); acc = 0; n = 0
        for c in cs:
            if acc >= need or c[0] < CORR_MIN: break
            acc += c[0]; n += 1
        row["c_" + rule] = (n, acc, need, acc + 1e-9 >= need, len([c for c in cs if c[0] >= CORR_MIN]), sum(c[0] for c in cs if c[0] >= CORR_MIN))
        if rule in ("none", "nbr"): corr_all[(r, rule)] = [c[:5] for c in cs]
        if rule == "none":
            pick = cs[:n]
            # sourced pieces that still render red (> 35, not banned) between pieces of the same road posted <= 35
            sred = []
            for x in S:
                if x["ok"] and not x["ban"] and 35 < x["mph"] < 99:
                    nb = [y for y in nbrs(x) if y["mph"] <= 35 and not y["ban"]]
                    if len({id(y) for y in nb}) >= 2: sred.append((x["L"], x["nm"] or "(unnamed)", x["mph"], x["hw"], "sourced_red", [x], True))
            conf = [c for c in cs if c[6] and c[0] >= CORR_MIN / 5]
            # rule 5: every shop/user report is a corridor to re-check, plus similar roads in the region
            rep = []
            for q in [q for q in REPORTS if q["region"] == r]:
                P = [q["lon"], q["lat"]]
                near = min(S, key=lambda x: min(math.hypot((p[0]-P[0])*math.cos(math.radians(P[1])), p[1]-P[1]) for p in x["g"]), default=None)
                if near is None: continue
                same = [c for c in cs if any(z is near for z in c[5])]
                cor = same[0] if same else (near["L"], near["nm"] or "(unnamed)", near["mph"], near["hw"], near["tier"], [near], False)
                similar = [c for c in cs if c is not cor and c[3] == cor[3] and c[2] == cor[2] and c[0] >= CORR_MIN][:10]
                rep.append(dict(report=q, corridor=dict(name=cor[1], mi=round(cor[0], 2), mph=cor[2]), similar=[dict(name=c[1], mi=round(c[0], 2)) for c in similar]))
            CHECK[r] = dict(reports=rep, conflicts=[dict(name=c[1], mi=round(c[0], 2), mph=c[2], kind=c[4] if c[4] == "sourced_red" else "neighbour_disagrees") for c in sorted(sred + conf, key=lambda c: -c[0])[:40]],
                            gap=[dict(name=c[1], mi=round(c[0], 2), mph=c[2], conflict=c[6]) for c in sorted(pick, key=lambda c: (not c[6], -c[0]))])
            row["n_conf"] = len(sred) + len(conf)
        if rule == "none" and r in os.environ.get("DUMP", "").split(","):
            DUMPED[r] = [dict(L=c[0], nm=c[1], mph=c[2], hw=c[3], tier=c[4], segs=[{k: v for k, v in y.items() if k in ("a", "b", "g", "osm", "way", "code", "L")} for y in c[5]],
                              cross={n: sorted(nodenames[n] - {c[1], ""}) for y in c[5] for n in (y["a"], y["b"])}) for c in cs[:n]]
    # v3 (relaxed bar, analysis only): grid streets excluded from the %, cited bans count as sourced
    NG = [x for x in S if not x["grid"]]
    row["v3_all"] = sum(x["L"] for x in NG); row["v3_ban"] = sum(x["L"] for x in NG if x["ban"])
    row["v3_ban_cited"] = sum(x["L"] for x in NG if x["ban"] and (x["ok"] or x["code"] == "v" or x.get("src")))
    row["v3_src_nb"] = sum(x["L"] for x in NG if x["ok"] and not x["ban"])
    row["ban_mi"] = sum(x["L"] for x in BANS); row["ban_src_mi"] = sum(x["L"] for x in BANS if x["ok"])
    row["grid_mi"] = sum(x["L"] for x in S if x["grid"]); row["county_assumed_mi"] = sum(x["L"] for x in S if x["code"] == "i" and COUNTY.search(x["nm"] or ""))
    row["assumed_mi"] = sum(x["L"] for x in S if x["code"] == "i" and not x["ban"])
    gap = collections.Counter()
    for x in S:
        if not (x["ok"] or id(x) in inf): gap[x["tier"]] += x["L"]
    row["gap"] = gap; out.append(row)
# Official beta bar (Max, 2026-10-22): >= 70% of important MILES backed by a real source. Corridors >= 0.25 mi are the to-do list.
STATUS = {}
for x in out:
    miss = ([] if x["s"] >= BAR else [f"miles {100*x['s']:.1f}% < 70%"]) + ([] if x["r"] in ACCESS else ["no local access source recorded"])
    STATUS[x["r"]] = dict(important_mi=round(x["L"], 1), sourced_pct=round(100*x["s"], 1), access_source=x["r"] in ACCESS,
                          passes=not miss, missing=miss, corridors_to_70=x["c_none"][0], corridor_mi_to_70=round(x["c_none"][1], 1),
                          conflicts=x["n_conf"], ban_mi=round(x["ban_mi"], 1), ban_sourced_mi=round(x["ban_src_mi"], 1),
                          grid_mi=round(x["grid_mi"], 1), county_assumed_mi=round(x["county_assumed_mi"], 1), assumed_mi=round(x["assumed_mi"], 1),
                          reports=len(CHECK.get(x["r"], {}).get("reports", [])))
V3 = {}
ACC3 = json.load(open(os.path.join(HERE, "access_sources.json")))
for x in out:
    a, b, bc, sn = x["v3_all"] or 1e-9, x["v3_ban"], x["v3_ban_cited"], x["v3_src_nb"]
    p_in = (sn + bc) / a; p_nb = sn / max(a - b, 1e-9)
    acc = x["r"] in ACC3["regions"] or x["r"] in ACC3.get("state_law", {})
    why = ([] if p_in >= BAR else [f"{100*p_in:.1f}% < 70% (bans in)"]) + ([] if p_nb >= 0.5 else [f"non-ban {100*p_nb:.1f}% < 50% floor"]) + ([] if acc else ["no local-rules search recorded"])
    V3[x["r"]] = dict(pct_bans_in=round(100*p_in, 1), pct_nonban=round(100*p_nb, 1), access_check=acc, passes=(not why) or x["r"] == "sd", why=["SD exempt"] if x["r"] == "sd" else why)
json.dump(dict(rule="v3 relaxed (analysis only): >=70% of important miles sourced with cited bans counted as sourced; >=50% of non-ban miles sourced; local-rules search recorded (ordinance or state law); grids/reports on check list only; sd exempt", regions=V3),
          open(os.path.join(HERE, os.environ.get("V3_OUT", "beta_status_v3.json")), "w"), indent=1, sort_keys=True)
json.dump(CHECK, open(os.path.join(HERE, "beta_check_list.json"), "w"), indent=1)
if not os.environ.get("NO_STATUS"):
    json.dump(dict(rule="pass = important miles (bans excluded) sourced by v/m/d+source >= 70% AND a local access source recorded; resort grids included when an access source exists; corridors >= 0.25 mi, conflicts and reports checked first; sd exempt (never beta)", regions=STATUS),
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "beta_status.json"), "w"), indent=1, sort_keys=True)
if DUMPED: json.dump(DUMPED, open("/tmp/bg2_dump.json", "w"))
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
