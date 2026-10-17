"""Load each hidden expansion region via ?r=<id>, check it builds, run a short sample route, screenshot to shots/exp-<id>.png."""
from playwright.sync_api import sync_playwright
import os, json, sys
URL = os.environ.get("URL", "http://localhost:8765/"); OUT = os.environ.get("SHOTS", "shots"); os.makedirs(OUT, exist_ok=True)
IDS = sys.argv[1:]; fails = []; res = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for rid in IDS:
        ctx = b.new_context(viewport={"width": 1280, "height": 860}); pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL + "?r=" + rid)
        try:
            pg.wait_for_function(f"window.ready===true&&REG.id==='{rid}'", timeout=180000)
        except Exception as e: print("FAIL", rid, "not ready", e); fails.append(rid); ctx.close(); continue
        c = pg.evaluate("REG.center"); pg.wait_for_timeout(4000)
        r = pg.evaluate(f"testRoute([{c[0]-0.006},{c[1]-0.006}],[{c[0]+0.006},{c[1]+0.006}])")
        pg.evaluate(f"map.setView([{c[0]},{c[1]}],14);0"); pg.wait_for_timeout(4000)
        pg.screenshot(path=f"{OUT}/exp-{rid}.png")
        ok = not errs; res[rid] = {"route": r and {k: r[k] for k in r if k in ("mi", "stretches")}, "errors": errs[:3]}
        print("PASS" if ok else "FAIL", rid, json.dumps(res[rid], default=str)[:300]); (None if ok else fails.append(rid)); ctx.close()
    b.close()
print("RESULT", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
