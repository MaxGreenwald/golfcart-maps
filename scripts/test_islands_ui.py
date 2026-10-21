"""Same-road islands in the app (scripts/islands.py). Soledad Mountain Rd's unnamed carriageway (Max, Oct 18 2026) must be green,
named, and say it takes the limit posted on both sides; a 'q' stretch (one OSM tag says 45 between posted-35 pieces) is drawn as
a dashed orange caution with a "Sources disagree ... Check posted signs" popup."""
from playwright.sync_api import sync_playwright
import os
URL = os.environ.get("URL", "http://localhost:8765/"); fails = []
def ck(n, c, x=""): print(("PASS " if c else "FAIL ") + n, x); c or fails.append(n)
POP = """(async(name,lat,lon,code)=>{await ensure(lat-0.02,lon-0.02,lat+0.02,lon+0.02);let s=null,bd=1;for(const x of D.segs){if(!x||D.names[x[0]]!==name||x[3]!==code)continue;const d=Math.abs(x[7][0][1]-lat)+Math.abs(x[7][0][0]-lon);if(d<bd){bd=d;s=x}}if(!s||bd>0.003)return 'NO SEG';const q=s[7][0];
 map.setView([q[1],q[0]],18);await new Promise(r=>setTimeout(r,1200));let pl=null;layer.eachLayer(g=>{(g.eachLayer?g:{eachLayer:f=>f(g)}).eachLayer(l=>{const A=l.getLatLngs&&l.getLatLngs(),ll=A&&A[0],lz=A&&A[A.length-1],z=s[7][s[7].length-1];if(ll&&Math.abs(ll.lat-q[1])<1e-6&&Math.abs(ll.lng-q[0])<1e-6&&Math.abs(lz.lat-z[1])<1e-6&&Math.abs(lz.lng-z[0])<1e-6)pl=l})});
 if(!pl)return 'NO LINE';pl.fire('click',{latlng:L.latLng(q[1],q[0])});await new Promise(r=>setTimeout(r,200));return {txt:(document.querySelector('.leaflet-popup-content')||{}).innerText||'',dash:pl.options.dashArray||'',color:pl.options.color,mph:s[2],cls:cls(s)}})"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
    pg.add_init_script("window.NO_TRACK=1"); pg.on("pageerror", lambda e: fails.append("js " + str(e)))
    pg.goto(URL); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(800)
    v = pg.evaluate(POP + "('Soledad Mountain Road',32.81562,-117.23579,'n')")
    ok = isinstance(v, dict)
    ck("Soledad carriageway is named and OK for LSVs", ok and "Soledad Mountain Road" in v["txt"] and "OK for LSVs" in v["txt"] and v["cls"] == 0, repr(v)[:300])
    ck("Soledad popup explains the inherited limit", ok and "same road posted on both sides" in v["txt"] and "posted 35 mph on both sides" in v["txt"], repr(v)[:300])
    ck("Soledad carriageway drawn solid green", ok and v["color"] == "#12a150" and not v["dash"], repr(v)[:160])
    v = pg.evaluate(POP + "('Gilman Drive',32.87234,-117.23773,'q')")
    ok = isinstance(v, dict)
    ck("sources-disagree stretch: dashed orange caution", ok and v["dash"] == "8 6" and v["color"] == "#f08c00", repr(v)[:200])
    ck("sources-disagree popup", ok and "Sources disagree" in v["txt"] and "Check posted signs" in v["txt"], repr(v)[:300])
    pg.evaluate("map.closePopup();0")
    r = pg.evaluate("testRoute([32.8172,-117.2363],[32.8113,-117.2316]).then(r=>r&&r.mi)"); pg.wait_for_timeout(400)
    ck("route along Soledad Mountain Rd found in LSV mode", bool(r), repr(r))
    b.close()
print("FAILS:", fails) if fails else print("ALL PASS"); raise SystemExit(1 if fails else 0)
