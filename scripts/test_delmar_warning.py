"""Del Mar speed ordinance (in force Nov 19 2026). The time-boxed "posted 40-45 mph until Nov 19" warning expired with it and must
never come back. The 3 stretches it covered are still signed 40/45/40, so until the new signs are confirmed (research/posted_limits.json)
they are built at the posted limit and are NOT LSV-legal: red Avoid line, popup note "Del Mar lowered this stretch to N mph on Nov 19,
2026. Until the new signs are confirmed, it's treated at the posted M mph, which is too fast for LSVs.", no caution styling.
Legal routes never use them; a risky route that does shows the note in its step and a summary flag. Checked on several device dates."""
from playwright.sync_api import sync_playwright
import os
from _check import ck, fail, finish
URL = os.environ.get("URL", "http://localhost:8765/")
A, B = [32.9595, -117.2655], [32.9918, -117.2717]   # Del Mar Plaza -> Fletcher Cove; every way north uses a blocked stretch
C = [32.9620, -117.2668]                              # Plaza -> Camino del Mar to the south: legal control route, no blocked road
POP = """(async(name,lat)=>{await ensure(32.95,-117.28,32.99,-117.25);const s=D.segs.find(x=>x&&D.names[x[0]]===name&&Math.abs(x[7][0][1]-lat)<0.004&&x[3]==='v');if(!s)return 'NO SEG';const q=s[7][0];
 map.setView([q[1],q[0]],17);await new Promise(r=>setTimeout(r,1200));let pl=null;layer.eachLayer(g=>{(g.eachLayer?g:{eachLayer:f=>f(g)}).eachLayer(l=>{const A=l.getLatLngs&&l.getLatLngs(),ll=A&&A[0],lz=A&&A[A.length-1],z=s[7][s[7].length-1];if(ll&&Math.abs(ll.lat-q[1])<1e-6&&Math.abs(ll.lng-q[0])<1e-6&&Math.abs(lz.lat-z[1])<1e-6&&Math.abs(lz.lng-z[0])<1e-6)pl=l})});
 if(!pl)return 'NO LINE';pl.fire('click',{latlng:L.latLng(q[1],q[0])});await new Promise(r=>setTimeout(r,200));return {txt:(document.querySelector('.leaflet-popup-content')||{}).innerText||'',dash:pl.options.dashArray||'',color:pl.options.color,mph:s[2],cls:cls(s)}})"""
# label fragment -> (popup road name, start lat, posted mph used now, ordinance mph)
STRETCHES = {"Camino del Mar (Via de la Valle - San Dieguito Bridge": ("Camino del Mar", 32.978, 40, 30),
             "Jimmy Durante Blvd (Fairgrounds Gate 2 - San Dieguito Dr": ("Jimmy Durante Boulevard", 32.972, 45, 30),
             "Via de la Valle (Camino del Mar - Jimmy Durante Blvd": ("Via de la Valle", 32.98, 40, 35)}
NOTE = "Del Mar lowered this stretch to {o} mph on Nov 19, 2026. Until the new signs are confirmed, it's treated at the posted {p} mph, which is too fast for LSVs."
COV = """(async(frags)=>{await ensure(32.94,-117.29,33.0,-117.24);const out={};for(const f of frags)out[f]={n:0,blk:0,adv:0,mph:{},cls:{}};let blkOther=0;
 for(const s of D.segs){if(!s)continue;const lab=JSON.stringify(D.sources[s[8]]||''),b=blkOf(s),f=frags.find(f=>lab.includes(f));
  if(f){const o=out[f];o.n++;if(b)o.blk++,o.txt=b.text;if(advOf(s))o.adv++;o.mph[s[2]]=(o.mph[s[2]]||0)+1;o.cls[cls(s)]=(o.cls[cls(s)]||0)+1}
  else if(b)blkOther++}
 return {out,blkOther}})"""
LEGS = "(()=>{const r=window._lastDetail;if(!r)return null;return r.legs.filter(l=>blkOf(l.s)).map(l=>!!l.f)})()"
OLD = ("drops to", "posted 40\u201345 mph until", "Posted 40 mph today", "Posted 45 mph today", "until Nov 19, 2026")
def run(today):
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
        pg.add_init_script("window.NO_TRACK=1;" + (f"window.GCM_TODAY='{today}'" if today else ""))
        pg.on("pageerror", lambda e: fail("js " + str(e)))
        pg.goto(URL); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(800)
        cov = pg.evaluate(COV, list(STRETCHES))
        pops = {f: pg.evaluate(POP + f"('{n}',{lat})") for f, (n, lat, _, _) in STRETCHES.items()}
        other = pg.evaluate(POP + "('Camino del Mar',32.962)")   # Coast Blvd - Plaza stretch: 30, LSV-legal, no note
        out = {}
        pg.evaluate("map.closePopup();0"); c = pg.evaluate(f"testRoute({A},{C}).then(r=>r&&r.mi)"); pg.wait_for_timeout(300)
        out['ctrl'] = (c, pg.evaluate(LEGS) if c else None, pg.inner_text("#steps"), pg.inner_text("#sub"))
        for rk in (False, True):
            pg.evaluate("map.closePopup();0"); r = pg.evaluate(f"testRoute({A},{B},{'true' if rk else 'false'}).then(r=>r&&r.mi)"); pg.wait_for_timeout(500)
            out[rk] = (r, pg.evaluate(LEGS) if r else None, pg.inner_text("#steps"), pg.inner_text("#sub"))
        b.close()
        return cov, pops, other, out
for today in ("2026-10-18", "2026-11-19", "2027-06-01", None):
    tag = today or "device date"
    cov, pops, other, out = run(today)
    for f, (n, lat, posted, ordm) in STRETCHES.items():
        o, note = cov["out"][f], NOTE.format(o=ordm, p=posted)
        ck(f"{tag}: {n} every segment at the posted {posted} mph", o["n"] > 0 and o["mph"] == {str(posted): o["n"]}, repr(o)[:240])
        ck(f"{tag}: {n} not LSV-legal on every segment (class 3)", o["cls"] == {"3": o["n"]}, repr(o["cls"]))
        ck(f"{tag}: {n} every segment carries the block note, no caution", o["blk"] == o["n"] and o["adv"] == 0 and o.get("txt") == note, repr(o)[:240])
        v = pops[f]; ok = isinstance(v, dict)
        ck(f"{tag}: {n} popup shows the note and Avoid", ok and note in v["txt"] and "Avoid" in v["txt"] and f"{posted} mph" in v["txt"], repr(v)[:260])
        ck(f"{tag}: {n} popup has no expired warning or caution", ok and not any(x in v["txt"] for x in OLD) and "Check posted signs" not in v["txt"], repr(v)[:160])
        ck(f"{tag}: {n} red Avoid line, not the caution dash", ok and v["dash"] != "8 6" and v["color"] == "#e5484d" and v["cls"] == 3, repr(v)[-120:])
    ck(f"{tag}: block note only on the 3 stretches", cov["blkOther"] == 0, repr(cov["blkOther"]))
    ck(f"{tag}: Coast Blvd - Plaza stretch legal, no note", isinstance(other, dict) and other["cls"] == 0 and "Del Mar lowered" not in other["txt"], repr(other)[:160])
    r, legs, steps, sub = out[False]
    ck(f"{tag}: legal route never drives a blocked stretch as legal", r is None or (legs is not None and all(legs)), repr((r, legs)))
    ck(f"{tag}: legal route has no expired warning", not any(x in steps or x in sub for x in OLD), (steps + sub)[:300])
    r, legs, steps, sub = out[True]
    if r:   # a risky route may cross a blocked stretch only as a flagged risky leg, with the note in its step
        ck(f"{tag}: risky route flags every blocked leg as risky", legs is not None and all(legs), repr(legs))
        if legs:
            ck(f"{tag}: risky route step shows the note", "Risky" in steps and "Until the new signs are confirmed" in steps, steps[:400])
            ck(f"{tag}: risky route summary flags it", "still signed 40-45 mph until new signs are confirmed" in sub, sub)
    else:
        ck(f"{tag}: no risky route either (blocked stretches are longer than the short-stretch allowance)", "connect these points" in sub, sub)
    ck(f"{tag}: risky route has no expired warning", not any(x in steps or x in sub for x in OLD), (steps + sub)[:300])
    c, legs, steps, sub = out['ctrl']
    ck(f"{tag}: control route in the Village still works, no blocked road", bool(c) and legs == [] and "Del Mar lowered" not in steps, repr((c, legs, steps[:120])))
finish()
