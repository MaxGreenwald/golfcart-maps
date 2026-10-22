#!/usr/bin/env python3
"""Beta-exit gap: share of important roads (primary/secondary/tertiary + _link; trunk only when <=TRUNK_MAX mph)
backed by a real source (v, m, or d with a source link). Usage: beta_exit_gap.py [trunk_max]"""
import json, glob, math, os, sys
TRUNK_MAX = int(sys.argv[1]) if len(sys.argv) > 1 else -1
IMP = {"primary", "secondary", "tertiary"}
def km(g): return sum(math.hypot((g[i][1]-g[i-1][1])*110.574, (g[i][0]-g[i-1][0])*111.32*math.cos(math.radians(g[i][1]))) for i in range(1, len(g)))
rows = []
for d in sorted(glob.glob("public/data/*/index.json")):
    r = d.split("/")[2]; seen = set(); n = ns = 0; L = Ls = 0.0
    for f in glob.glob(f"public/data/{r}/tiles/*.json"):
        for s in json.load(open(f)):
            hw = s[1].replace("_link", "")
            if not (hw in IMP or (hw == "trunk" and s[2] <= TRUNK_MAX)): continue
            k = (min(s[5], s[6]), max(s[5], s[6]))
            if k in seen: continue
            seen.add(k); l = km(s[7]); src = len(s) > 8 and s[8] >= 0
            ok = s[3] in ("v", "m") or (s[3] == "d" and src)
            n += 1; ns += ok; L += l; Ls += l * ok
    need = max(0, math.ceil(0.7 * n - ns))
    rows.append((r, n, ns, L*0.621371, Ls*0.621371, need))
print("| Region | Important segs | Sourced | % segs | Important mi | Sourced mi | % miles | Segs to 70% | Batches (1,000) |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for r, n, ns, L, Ls, need in sorted(rows, key=lambda x: -x[2]/max(x[1],1)):
    print(f"| {r} | {n:,} | {ns:,} | {100*ns/max(n,1):.1f}% | {L:,.1f} | {Ls:,.1f} | {100*Ls/max(L,1e-9):.1f}% | {need:,} | {math.ceil(need/1000)} |")
T = [sum(x[i] for x in rows) for i in (1, 2, 3, 4, 5)]
print(f"| **All {len(rows)}** | {T[0]:,} | {T[1]:,} | {100*T[1]/T[0]:.1f}% | {T[2]:,.0f} | {T[3]:,.0f} | {100*T[3]/T[2]:.1f}% | {T[4]:,} | {sum(math.ceil(x[5]/1000) for x in rows)} |")
print(f"\nPassing (>=70% by segments): {sum(1 for x in rows if x[5]==0)}/{len(rows)}")
