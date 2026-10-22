#!/usr/bin/env python3
"""Set the "beta" flag in public/data/regions.json from research/beta_status.json (written by research/beta_exit_gap_v2.py).
Bar (Max, 2026-10-22): a region leaves beta when >= 70% of its important-road miles are backed by a real source.
San Diego is always exempt and never beta (Max: "keep san Diego live tho no beta").
Usage: apply_beta_bar.py [--check]   (--check: exit 1 if regions.json disagrees, write nothing)"""
import json, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EXEMPT = {"sd"}
def wanted():
    st = json.load(open(os.path.join(ROOT, "research/beta_status.json")))["regions"]
    return {rid: (False if rid in EXEMPT else not v["passes"]) for rid, v in st.items()}
def main():
    p = os.path.join(ROOT, "public/data/regions.json"); raw = open(p).read(); regs = json.loads(raw); w = wanted(); diff = []
    for r in regs:
        if r["id"] not in w: continue
        if bool(r.get("beta")) != w[r["id"]]:
            diff.append((r["id"], bool(r.get("beta")), w[r["id"]]))
            if w[r["id"]]: r["beta"] = True
            else: r.pop("beta", None)
    for d in diff: print(f"{d[0]}: beta {d[1]} -> {d[2]}")
    if "--check" in sys.argv: sys.exit(1 if diff else 0)
    if diff:
        ind = 1 if "\n " in raw else None
        open(p, "w").write(json.dumps(regs, indent=ind, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
if __name__ == "__main__": main()
