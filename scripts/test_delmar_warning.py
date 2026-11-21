"""Del Mar speed ordinance (took effect Nov 19 2026). The time-boxed "posted 40-45 mph until Nov 19" warning expired with it and
must never come back. The 3 stretches it covered now carry the no-expiry safety caution (CAU list in public/app.js, same as
La Jolla Blvd): dashed orange line, popup line "new signs may not be up yet. Check posted signs.", route-step note and route
summary note, on every date until the new signs are confirmed. Speeds and legality stay the ordinance values (30 / 30 / 35, LSV OK)."""
from playwright.sync_api import sync_playwright
import os
from _check import ck, fail, finish
URL = os.environ.get("URL", "http://localhost:8765/")
ROUTE = "testRoute([32.9595,-117.2655],[32.9918,-117.2717]).then(r=>r&&r.mi)"   # Del Mar Plaza -> Fletcher Cove, uses Camino del Mar over the bridge
POP = """(async(name,lat)=>{await ensure(32.95,-117.28,32.99,-117.25);const s=D.segs.find(x=>x&&D.names[x[0]]===name&&Math.abs(x[7][0][1]-lat)<0.004&&x[3]==='v');if(!s)return 'NO SEG';const q=s[7][0];
 map.setView([q[1],q[0]],17);await new Promise(r=>setTimeout(r,1200));let pl=null;layer.eachLayer(g=>{(g.eachLayer?g:{eachLayer:f=>f(g)}).eachLayer(l=>{const A=l.getLatLngs&&l.getLatLngs(),ll=A&&A[0],lz=A&&A[A.length-1],z=s[7][s[7].length-1];if(ll&&Math.abs(ll.lat-q[1])<1e-6&&Math.abs(ll.lng-q[0])<1e-6&&Math.abs(lz.lat-z[1])<1e-6&&Math.abs(lz.lng-z[0])<1e-6)pl=l})});
 if(!pl)return 'NO LINE';pl.fire('click',{latlng:L.latLng(q[1],q[0])});await new Promise(r=>setTimeout(r,200));return {txt:(document.querySelector('.leaflet-popup-content')||{}).innerText||'',dash:pl.options.dashArray||'',color:pl.options.color,mph:s[2],cls:cls(s)}})"""
# label fragment -> (popup road name, start lat, ordinance mph, old posted mph)
STRETCHES = {"Camino del Mar (Via de la Valle - San Dieguito Bridge": ("Camino del Mar", 32.978, 30, 40),
             "Jimmy Durante Blvd (Fairgrounds Gate 2 - San Dieguito Dr": ("Jimmy Durante Boulevard", 32.972, 30, 45),
             "Via de la Valle (Camino del Mar - Jimmy Durante Blvd": ("Via de la Valle", 32.98, 35, 40)}
COV = """(async(frags)=>{await ensure(32.94,-117.29,33.0,-117.24);const out={};for(const f of frags)out[f]={n:0,cau:0,bad:[]};let dmOther=0;
 for(const s of D.segs){if(!s)continue;const lab=JSON.stringify(D.sources[s[8]]||''),a=advOf(s),t=a&&a.text||'';const f=frags.find(f=>lab.includes(f));
  if(f){const o=out[f];o.n++;if(/new signs may not be up yet\\. Check posted signs\\./.test(t)&&t.includes('Nov 19, 2026'))o.cau++;else o.bad.push(t||'none');
   o.mph=o.mph||{};o.mph[s[2]]=(o.mph[s[2]]||0)+1;o.st=o.st||{};o.st[s[3]+':'+cls(s)]=(o.st[s[3]+':'+cls(s)]||0)+1}
  else if(/Del Mar lowered this stretch/.test(t))dmOther++}
 return {out,dmOther}})"""
OLD = ("drops to", "posted 40\u201345 mph until", "Posted 40 mph today", "Posted 45 mph today")
def run(today):
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
        pg.add_init_script("window.NO_TRACK=1;" + (f"window.GCM_TODAY='{today}'" if today else ""))
        pg.on("pageerror", lambda e: fail("js " + str(e)))
        pg.goto(URL); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(800)
        cov = pg.evaluate(COV, list(STRETCHES))
        pops = {f: pg.evaluate(POP + f"('{n}',{lat})") for f, (n, lat, _, _) in STRETCHES.items()}
        other = pg.evaluate(POP + "('Camino del Mar',32.962)")   # Coast Blvd - Plaza stretch: 30 by ordinance, never posted above 35, no caution
        pg.evaluate("map.closePopup();0"); r = pg.evaluate(ROUTE); pg.wait_for_timeout(500)
        steps, sub = pg.inner_text("#steps"), pg.inner_text("#sub"); b.close()
        return cov, pops, other, r, steps, sub
# before, on and after the ordinance date, and the real device date: the caution never expires, the old warning never returns
for today in ("2026-10-18", "2026-11-19", "2027-06-01", None):
    tag = today or "device date"
    cov, pops, other, r, steps, sub = run(today)
    for f, (n, lat, mph, old) in STRETCHES.items():
        o = cov["out"][f]
        ck(f"{tag}: {n} every segment carries the no-expiry caution", o["n"] > 0 and o["cau"] == o["n"], repr(o)[:240])
        ck(f"{tag}: {n} speed unchanged ({mph} mph on every segment)", o.get("mph") == {str(mph): o["n"]}, repr(o.get("mph")))
        ck(f"{tag}: {n} legality unchanged (posted OK for LSVs, class 0)", o.get("st") and all(k == "v:0" for k in o["st"]), repr(o.get("st")))
        v = pops[f]; ok = isinstance(v, dict)
        ck(f"{tag}: {n} popup caution", ok and f"from {old} to {mph} mph on Nov 19, 2026" in v["txt"] and "new signs may not be up yet. Check posted signs." in v["txt"], repr(v)[:240])
        ck(f"{tag}: {n} popup has no expired warning", ok and not any(x in v["txt"] for x in OLD), repr(v)[:160])
        ck(f"{tag}: {n} dashed orange, {mph} mph", ok and v["dash"] == "8 6" and v["color"] == "#f08c00" and v["mph"] == mph, repr(v)[:160])
    ck(f"{tag}: Del Mar caution only on the 3 stretches", cov["dmOther"] == 0, repr(cov["dmOther"]))
    ck(f"{tag}: other Del Mar stretch has no caution", isinstance(other, dict) and "Check posted signs" not in other["txt"] and other["dash"] != "8 6", repr(other)[:160])
    ck(f"{tag}: route uses the stretch", bool(r), repr(r))
    ck(f"{tag}: route step shows the caution", "Del Mar lowered this stretch from 40 to 30 mph on Nov 19, 2026" in steps and "Check posted signs" in steps, steps[:300])
    ck(f"{tag}: route summary flags it", "posted signs may not match our data" in sub, sub)
    ck(f"{tag}: no expired warning in route", not any(x in steps or x in sub for x in OLD), (steps + sub)[:300])
finish()
