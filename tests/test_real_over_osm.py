"""Max's rule (Oct 20 2026): a real source (official data, Street View / Mapillary sign, survey) overrides OSM; OSM alone never
blocks 'verified' or makes 'disagree'; real sources that conflict stay 'disagree'. Plus the data checks it produced."""
import ast, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); GT = os.path.join(HERE, "..", "research", "sd_ground_truth")
src = open(os.path.join(GT, "analyze.py")).read(); tree = ast.parse(src)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "classify")
ns = {}; exec(compile(ast.Module([fn], []), "classify", "exec"), ns); C = lambda *s: ns["classify"](list(s))[0]
O = lambda v: ("official", v, "", ""); M = lambda v: ("osm", v, "", ""); S = lambda v: ("streetview", v, "", ""); Y = lambda v: ("mapillary", v, "", "")
fails = []
def eq(a, b, what):
    print("ok " if a == b else "FAIL", what, a); a == b or fails.append(what)
eq(C(O(50), M(30), S(50)), "verified", "official + sign agree, OSM disagrees -> verified")
eq(C(O(50), M(30)), "one official source", "official vs OSM only -> one official source (not disagree)")
eq(C(O(35), M(35)), "verified", "Batch 0: official + OSM agree -> verified")
eq(C(O(35), S(25)), "disagree", "official vs sign -> disagree (unresolved)")
eq(C(S(30), S(35), M(45)), "disagree", "two signs conflict -> disagree")
eq(C(S(35), Y(35), M(45)), "OSM + imagery agree (no official source)", "two signs agree, OSM differs -> not disagree")
eq(C(S(30), M(45)), "one unofficial source", "one sign vs OSM -> one unofficial source")
eq(C(M(30)), "one unofficial source", "OSM only")
eq(C(), "no posted-limit source (state default assumed)", "no source")
R = {r["osm_way"]: r for r in csv.DictReader(open(os.path.join(GT, "segments.csv")))}
cb = [r for r in R.values() if r["road"] == "Carlsbad Boulevard" and r["verified_mph"] == "50"]
eq(len(cb) >= 7, True, f"Carlsbad Blvd 50 mph (official + sign) verified ways >= 7 (got {len(cb)})")
sol = R.get("780284924")
eq(sol and sol["map_mph"], "35", "South Coast Hwy, Solana Beach (Estrella - Lomas Santa Fe): map uses the posted/E&TS 35, not Encinitas' 30")
print("RESULT", "ALL PASS" if not fails else f"{len(fails)} FAIL"); sys.exit(1 if fails else 0)
