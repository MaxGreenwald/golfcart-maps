"""Route choices on an iPhone viewport with 4x CPU throttle: options render, every option is legal (no forbidden
segment unless Risky), picking one redraws it and is remembered, % verified shows, avoid-crossings toggle, timing."""
from playwright.sync_api import sync_playwright
import os,sys,json
URL=os.environ.get("URL","http://localhost:8765/");fails=[];BUDGET=float(os.environ.get("BUDGET_MS","2500"))
def ck(n,c,x=""):print("PASS" if c else "FAIL",n,"" if c else str(x)[:400]);(None if c else fails.append(n))
TRIPS=[([32.8328,-117.2713],[32.8180,-117.2700]),([32.7976,-117.2531],[32.8090,-117.2580]),([32.9590,-117.2650],[32.9930,-117.2710])]
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page()
    pg.on("pageerror",lambda e:fails.append("js error "+str(e)))
    pg.add_init_script("localStorage.setItem('gcm-notrack','1')")
    pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000);pg.wait_for_timeout(1500)
    cdp=ctx.new_cdp_session(pg);cdp.send("Emulation.setCPUThrottlingRate",{"rate":4})
    for a,z in TRIPS:
        pg.evaluate(f"testRoute({a},{z})")  # warm tiles
        r=pg.evaluate(f"testRoute({a},{z})");ms=pg.evaluate("_routeMs");o=pg.evaluate("_routeOpts.map(o=>({id:o.id,also:o.also,mi:+(o.dist/1609.34).toFixed(2),min:o.min,score:o.score,bad:o.parts.filter(([si])=>cls(D.segs[si])===3).length}))")
        print(" ",a,z,ms,"ms",json.dumps(o))
        ck(f"options found {a}",len(o)>=1 and o[0]["id"]=="fastest",o)
        ck(f"all options legal {a}",all(x["bad"]==0 for x in o),o)
        ck(f"4 choices covered {a}",sorted(sum([[x["id"]]+x["also"] for x in o],[]))==sorted(["fastest","legal","shortest","scenic"]),o)
        ck(f"shortest is shortest {a}",min(o,key=lambda x:x["mi"])["mi"]>=[x for x in o if x["id"]=="shortest" or "shortest" in x["also"]][0]["mi"]-0.01,o)
        ck(f"options in {BUDGET:.0f} ms at 4x CPU {a}",ms<BUDGET,ms)
    ck("options shown in sheet",pg.locator("#ropts .ro").count()>=1 and "% verified" in pg.inner_text("#ropts"))
    n=pg.locator("#ropts .ro").count()
    if n>1:
        pg.locator("#ropts .ro").nth(n-1).click();pg.wait_for_function("document.querySelector('#ropts .ro.on')&&document.querySelector('#ropts .ro.on')===document.querySelectorAll('#ropts .ro')[document.querySelectorAll('#ropts .ro').length-1]",timeout=20000)
        sel=pg.evaluate("lastRoute.opt");ck("pick remembered",pg.evaluate("localStorage.getItem('gcm-ropt')")==sel,sel)
    if os.environ.get("SHOT"):cdp.send("Emulation.setCPUThrottlingRate",{"rate":1});pg.screenshot(path="shots/route-options.png")
    pg.evaluate("setROpt('fastest')")
    # avoid crossings: route still found (falls back with a note if impossible), and never crosses when it reports success
    pg.evaluate("setAvoid(true)");r=pg.evaluate(f"testRoute({TRIPS[0][0]},{TRIPS[0][1]})");ck("avoid on: route found",bool(r))
    ok=pg.evaluate("_routeOpts[0].avoidFailed||_routeOpts[0].parts.every(([si,rev],i,arr)=>{if(i===arr.length-1)return true;const s=D.segs[si],n=rev?s[5]:s[6];return !fnode.has(n)||cnode.has(n)})")
    ck("avoid on: no fast-road crossings (or labeled fallback)",ok)
    pg.evaluate("setAvoid(false)")
    r=pg.evaluate(f"testRoute({TRIPS[0][0]},{TRIPS[0][1]},true)");ck("risky still works",bool(r))
    b.close()
print("RESULT","ALL PASS" if not fails else "FAIL "+str(fails));sys.exit(1 if fails else 0)
