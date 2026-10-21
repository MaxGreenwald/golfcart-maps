"""Route every trip in routes.json through the real app router (Playwright) and dump the legs it uses.
Usage: (cd public && python3 -m http.server 8765 &) ; python3 research/sd_ground_truth/export_routes.py"""
import json, os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); URL = os.environ.get("URL", "http://localhost:8765/")
R = json.load(open(os.path.join(HERE, "routes.json"))); P = R["places"]; out = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.add_init_script("window.NO_TRACK=1")
    pg.goto(URL); pg.wait_for_function("window.ready===true", timeout=120000)
    for a, z in R["routes"]:
        A, Z = P[a], P[z]
        res = pg.evaluate(f"""(async()=>{{const r=await testRoute([{A[2]},{A[3]}],[{Z[2]},{Z[3]}],false);if(!r)return null;const d=window._lastDetail;
          return {{mi:r.mi,legs:d.legs.map(l=>({{name:D.names[l.s[0]]||'',hw:l.s[1],mph:l.s[2],src:l.s[3],a:l.s[7][0],z:l.s[7][l.s[7].length-1],m:Math.round(l.s._len||0),risky:!!l.f}}))}}}})()""")
        if not res:  # no legal route: record the risky route too, so the roads that block it get checked as well
            res2 = pg.evaluate(f"""(async()=>{{const r=await testRoute([{A[2]},{A[3]}],[{Z[2]},{Z[3]}],true);if(!r)return null;const d=window._lastDetail;
              return {{mi:r.mi,legs:d.legs.map(l=>({{name:D.names[l.s[0]]||'',hw:l.s[1],mph:l.s[2],src:l.s[3],a:l.s[7][0],z:l.s[7][l.s[7].length-1],m:Math.round(l.s._len||0),risky:!!l.f}}))}}}})()""")
        print(a, "->", z, (f"no legal route; risky {res2['mi']} mi" if res2 else "no route even risky") if not res else f"{res['mi']} mi, {len(res['legs'])} legs", flush=True)
        out.append({"from": a, "to": z, "city": A[0], "ok": bool(res), "mi": (res or res2 or {}).get("mi"), "legs": (res or res2 or {}).get("legs", [])})
json.dump(out, open(os.path.join(HERE, "route_legs.json"), "w"))
