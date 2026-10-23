#!/usr/bin/env python3
"""Before/after for Street View batch 4 (same measures as research/streetview_batch2/report.py): per-row final limit and
legality flip, green miles per region, and the rows not applied. Green (LSV) = a segment at <=35 mph (bans are 99);
cart = <=25 and no golf-cart ban flag (rough cross-check only). usage: report.py BEFORE_DATA_DIR [AFTER_DATA_DIR]"""
import csv, importlib.util, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sv4_resolve", os.path.join(HERE, "resolve.py")); R = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(R)
B = sys.argv[1]; A = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "..", "public", "data")
def load(D, rid):
    idx = json.load(open(os.path.join(D, rid, "index.json"))); return idx, [s for t in idx["meta"]["tiles"] for s in json.load(open(os.path.join(D, rid, "tiles", t + ".json")))]
def cart_banned(s): return len(s) > 9 and s[9] == 1
def ok(m, s, lim): return m not in (None, 0, 99) and m <= lim and not (lim <= 25 and cart_banned(s))
def miles(D, rid):
    _, segs = load(D, rid); g = c = 0.0
    for s in segs:
        l = R.L(s[7]) / 1609.344
        if ok(s[2], s, 35): g += l
        if ok(s[2], s, 25): c += l
    return round(g, 2), round(c, 2)
signs = json.load(open(os.path.join(HERE, "signs.json")))
rows = {r["check_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "results.csv")))}
def leg(m): return "no" if m in (None, "", 99) or float(m) > 35 else "cart+LSV" if float(m) <= 25 else "LSV"
flips = []
for cid in sorted({e["check_id"] for v in signs.values() for e in v}):
    r = rows[cid]; was = r["our_speed_mph"]; now = int(float(r["posted_speed_seen_mph"])); a, b = leg(was), leg(now)
    flips.append({"check_id": cid, "region": r["region"], "road": r["road_name"], "from": r["from_cross_street"], "to": r["to_cross_street"], "kind": R.kind(r),
                  "was_mph": int(float(was)) if was else None, "now_mph": now, "was": a, "now": b, "confidence": r["confidence"], "imagery_date": r["imagery_date"],
                  "flip": "" if (a == "no") == (b == "no") else ("IN" if b != "no" else "OUT"),
                  "cart_flip": "" if (a == "cart+LSV") == (b == "cart+LSV") else ("cart IN" if b == "cart+LSV" else "cart OUT"), "gcm_ref": r["gcm_ref"]})
gm = {rid: {"before": miles(B, rid), "after": miles(A, rid)} for rid in sorted(signs)}
unres = json.load(open(os.path.join(HERE, "unresolved.json")))
json.dump({"flips": flips, "green_miles": gm, "not_applied": unres}, open(os.path.join(HERE, "report.json"), "w"), indent=1, ensure_ascii=False)
for f in flips:
    if f["flip"] or f["cart_flip"]: print(f["flip"] or "-", f["cart_flip"] or "-", f["region"], f["check_id"], f["road"], f["was_mph"], "->", f["now_mph"], f["kind"])
for rid, v in gm.items(): print(rid, "LSV green mi", v["before"][0], "->", v["after"][0], "(%+.2f)" % (v["after"][0] - v["before"][0]), "| cart", v["before"][1], "->", v["after"][1])
print("not applied:", [(u["check_id"], u["why"]) for u in unres])
