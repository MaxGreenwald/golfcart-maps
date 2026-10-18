"""Del Mar ordinance advisory: the 3 stretches still posted 40-45 mph until Nov 19 2026 get a dashed orange line, a popup
warning and a route-step warning; on/after Nov 19 2026 (device date, America/Los_Angeles) the warning disappears."""
from playwright.sync_api import sync_playwright
import os
URL = os.environ.get("URL", "http://localhost:8765/"); fails = []
def ck(n, c, x=""): print(("PASS " if c else "FAIL ") + n, x); c or fails.append(n)
ROUTE = "testRoute([32.9595,-117.2655],[32.9918,-117.2717]).then(r=>r&&r.mi)"   # Del Mar Plaza -> Fletcher Cove, uses Camino del Mar over the bridge
POP = """(async(name,lat)=>{await ensure(32.95,-117.28,32.99,-117.25);const s=D.segs.find(x=>D.names[x[0]]===name&&Math.abs(x[7][0][1]-lat)<0.004&&x[3]==='v');if(!s)return 'NO SEG';const q=s[7][0];
 map.setView([q[1],q[0]],17);await new Promise(r=>setTimeout(r,1200));let pl=null;layer.eachLayer(g=>{(g.eachLayer?g:{eachLayer:f=>f(g)}).eachLayer(l=>{const A=l.getLatLngs&&l.getLatLngs(),ll=A&&A[0],lz=A&&A[A.length-1],z=s[7][s[7].length-1];if(ll&&Math.abs(ll.lat-q[1])<1e-6&&Math.abs(ll.lng-q[0])<1e-6&&Math.abs(lz.lat-z[1])<1e-6&&Math.abs(lz.lng-z[0])<1e-6)pl=l})});
 if(!pl)return 'NO LINE';pl.fire('click',{latlng:L.latLng(q[1],q[0])});await new Promise(r=>setTimeout(r,200));return {txt:(document.querySelector('.leaflet-popup-content')||{}).innerText||'',dash:pl.options.dashArray||'',color:pl.options.color}})"""
def run(today):
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
        pg.add_init_script(f"window.NO_TRACK=1;" + (f"window.GCM_TODAY='{today}'" if today else ""))
        pg.on("pageerror", lambda e: fails.append("js " + str(e)))
        pg.goto(URL); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(800)
        res = {}
        cov = pg.evaluate("""(async()=>{await ensure(32.94,-117.29,33.0,-117.24);let flagged=0,want=0,miss=0;const re=/Via de la Valle - San Dieguito Bridge|Fairgrounds Gate 2 - San Dieguito|Camino del Mar - Jimmy Durante/;
          for(const s of D.segs){if(!s)continue;const a=!!advOf(s);const w=s[3]==='v'&&re.test(JSON.stringify(D.sources[s[8]]||''));flagged+=a;want+=w;if(w&&!a)miss++}return {flagged,want,miss}})()""")
        res['_cov'] = cov
        for name, lat in [("Camino del Mar", 32.978), ("Jimmy Durante Boulevard", 32.972), ("Via de la Valle", 32.98)]:
            res[name] = pg.evaluate(POP + f"('{name}',{lat})")
        other = pg.evaluate(POP + "('Camino del Mar',32.962)")   # Coast Blvd - Plaza stretch: 35->30, legal either way, no warning
        pg.evaluate("map.closePopup();0"); r = pg.evaluate(ROUTE); pg.wait_for_timeout(500)
        steps, sub = pg.inner_text("#steps"), pg.inner_text("#sub"); b.close()
        return res, other, r, steps, sub
res, other, r, steps, sub = run("2026-10-18")
cov = res.pop('_cov'); ck("all 3 ordinance stretches flagged, nothing else", cov['want'] > 0 and cov['miss'] == 0 and cov['flagged'] == cov['want'], repr(cov))
for n, v in res.items():
    ck(f"before Nov 19: {n} popup warns", isinstance(v, dict) and "drops to" in v["txt"] and "Nov 19, 2026" in v["txt"], repr(v)[:200])
    ck(f"before Nov 19: {n} dashed orange", isinstance(v, dict) and v["dash"] == "8 6" and v["color"] == "#f08c00")
ck("other Del Mar stretch has no warning", isinstance(other, dict) and "drops to" not in other["txt"], repr(other)[:160])
ck("route uses the stretch", bool(r), repr(r))
ck("route step shows the warning", "Posted 40 mph today" in steps and "Nov 19, 2026" in steps, steps[:300])
ck("route summary flags it", "posted 40–45 mph until Nov 19, 2026" in sub, sub)
res, other, r, steps, sub = run("2026-11-19")
cov = res.pop('_cov'); ck("on Nov 19: nothing flagged", cov['flagged'] == 0, repr(cov))
for n, v in res.items():
    ck(f"on Nov 19: {n} no warning, normal style", isinstance(v, dict) and "drops to" not in v["txt"] and v["dash"] != "8 6", repr(v)[:160])
ck("on Nov 19: no step warning", "Nov 19, 2026" not in steps and "Nov 19, 2026" not in sub)
print("FAILS:", fails) if fails else print("ALL PASS"); raise SystemExit(1 if fails else 0)
