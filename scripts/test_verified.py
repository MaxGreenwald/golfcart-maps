"""'Verified' is claimed only for coastal San Diego segments with two agreeing sources (data/sd/verified.json).
Checks: a verified SD road shows the badge + last-verified date; an SD road that isn't verified shows a confidence
level and no 'verified'; city/county-sourced roads say 'city/county source'; other regions never say 'verified'."""
from playwright.sync_api import sync_playwright
import os, json
URL = os.environ.get("URL", "http://localhost:8765/"); fails = []
def ck(n, c, x=""): print(("PASS " if c else "FAIL ") + n, x); c or fails.append(n)
POP = """(async(want)=>{if(REG.id==="sd")await ensure(32.53,-117.42,33.3,-117.1);await new Promise(r=>setTimeout(r,800));const out=[];for(const s of D.segs){if(out.length>=1)break;if(!want(s))continue;
  const q=s[7][0];map.setView([q[1],q[0]],17);await new Promise(r=>setTimeout(r,900));let pl=null;const z=s[7][s[7].length-1];layer.eachLayer(g=>(g.eachLayer?g:{eachLayer:f=>f(g)}).eachLayer(l=>{const A=l.getLatLngs&&l.getLatLngs();if(A&&A.length&&Math.abs(A[0].lat-q[1])<1e-6&&Math.abs(A[0].lng-q[0])<1e-6&&Math.abs(A[A.length-1].lat-z[1])<1e-6&&Math.abs(A[A.length-1].lng-z[0])<1e-6)pl=l}));
  if(!pl)continue;pl.fire('click',{latlng:L.latLng(q[1],q[0])});await new Promise(r=>setTimeout(r,200));const p=document.querySelector('.leaflet-popup-content');out.push(p?p.innerText:'')}return out[0]||null})"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900}); pg.add_init_script("window.NO_TRACK=1")
    pg.on("pageerror", lambda e: fails.append("js " + str(e)))
    pg.goto(URL); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(1500)
    ck("SD loads verified.json", pg.evaluate("!!(window.verOf&&document.getElementById('dmeta').textContent.includes('last verified'))"), pg.inner_text("#dmeta"))
    t = pg.evaluate(POP + "(s=>!!verOf(s))"); ck("verified SD road: badge + date", bool(t) and "Verified: 2 sources agree" in t and "last verified" in t, repr(t)[:200])
    t = pg.evaluate(POP + "(s=>!verOf(s)&&s[3]==='v'&&/sandiego\\.gov|ecode360/.test((D.sources[s[8]]||[''])[0]))"); ck("unverified city-sourced road: 'city/county source', no 'Verified'", bool(t) and "city/county source" in t and "erified" not in t and "Confidence: Medium" in t, repr(t)[:200])
    t = pg.evaluate(POP + "(s=>!verOf(s)&&s[3]==='i'&&s[2]===25)"); ck("assumed SD road: low confidence, no 'Verified'", bool(t) and "Confidence: Low" in t and "erified" not in t, repr(t)[:200])
    for rid in ["villages", "destin", "oob"]:
        pg.evaluate(f"loadRegion('{rid}')"); pg.wait_for_function("window.ready===true&&REG&&REG.id==='%s'" % rid, timeout=120000); pg.wait_for_timeout(800)
        t = pg.evaluate(POP + "(s=>s[3]==='v')") or pg.evaluate(POP + "(s=>true)")
        ck(f"{rid}: no 'verified' anywhere", t is not None and "erified" not in t and "erified" not in pg.inner_text("#dmeta"), repr(t)[:160])
print("FAILS:", fails) if fails else print("ALL PASS"); raise SystemExit(1 if fails else 0)
