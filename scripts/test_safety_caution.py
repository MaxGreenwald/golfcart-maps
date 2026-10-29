"""SD safety cautions (Oct 18 2026): La Jolla Blvd (Loring-Colima, posted 35 in Jan 2025 photos), Mission Blvd (posted 30 in
Jan 2025 photos; San Fernando-Santa Clara stretch) and Lomas Santa Fe Dr at Hwy 101 (OSM says 50) get the Del Mar-style
dashed orange line, a "Check posted signs" popup line and a route-step warning. Unlike the Del Mar advisory they don't expire."""
from playwright.sync_api import sync_playwright
import os
from _check import ck, fail, finish
URL = os.environ.get("URL", "http://localhost:8765/")
POP = """(async(name,lat,lon)=>{await ensure(lat-0.02,lon-0.02,lat+0.02,lon+0.02);let s=null,bd=1;for(const x of D.segs){if(!x||D.names[x[0]]!==name||x[3]!=='v')continue;const d=Math.abs(x[7][0][1]-lat)+Math.abs(x[7][0][0]-lon);if(d<bd){bd=d;s=x}}if(!s||bd>0.003)return 'NO SEG';const q=s[7][0];
 map.setView([q[1],q[0]],18);await new Promise(r=>setTimeout(r,1200));let pl=null;layer.eachLayer(g=>{(g.eachLayer?g:{eachLayer:f=>f(g)}).eachLayer(l=>{const A=l.getLatLngs&&l.getLatLngs(),ll=A&&A[0],lz=A&&A[A.length-1],z=s[7][s[7].length-1];if(ll&&Math.abs(ll.lat-q[1])<1e-6&&Math.abs(ll.lng-q[0])<1e-6&&Math.abs(lz.lat-z[1])<1e-6&&Math.abs(lz.lng-z[0])<1e-6)pl=l})});
 if(!pl)return 'NO LINE';pl.fire('click',{latlng:L.latLng(q[1],q[0])});await new Promise(r=>setTimeout(r,200));return {txt:(document.querySelector('.leaflet-popup-content')||{}).innerText||'',dash:pl.options.dashArray||'',color:pl.options.color,mph:s[2]}})"""
CASES = [("La Jolla Boulevard", 32.8100, -117.2655, 35, "show 35 mph"),
         ("La Jolla Boulevard", 32.8054, -117.2589, 35, "show 35 mph"),
         ("Mission Boulevard", 32.8030, -117.2575, 30, "show 30 mph"),
         ("Mission Boulevard", 32.7880, -117.2535, 30, "show 30 mph"),
         ("Mission Boulevard", 32.7725, -117.2512, 25, "showed 30 mph"),
         ("Lomas Santa Fe Drive", 32.9919, -117.2715, 35, "OpenStreetMap says 50")]
CLEAR = [("Prospect Street", 32.8477, -117.2745), ("South Coast Highway", 33.01355, -117.27989), ("South Coast Highway", 33.03812, -117.29279)]
for today in ("2026-10-18", "2026-11-19"):   # cautions must survive the Del Mar advisory's Nov 19 expiry
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
        pg.add_init_script(f"window.NO_TRACK=1;window.GCM_TODAY='{today}'")
        pg.on("pageerror", lambda e: fail("js " + str(e)))
        pg.goto(URL); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(800)
        for name, lat, lon, mph, frag in CASES:
            v = pg.evaluate(POP + f"('{name}',{lat},{lon})")
            ok = isinstance(v, dict)
            ck(f"{today} {name} @{lat}: popup caution", ok and "Check posted signs" in v["txt"] and frag in v["txt"], repr(v)[:220])
            ck(f"{today} {name} @{lat}: dashed orange, {mph} mph", ok and v["dash"] == "8 6" and v["color"] == "#f08c00" and v["mph"] == mph, repr(v)[:120])
        for name, lat, lon in CLEAR:
            v = pg.evaluate(POP + f"('{name}',{lat},{lon})")
            ck(f"{today} {name} @{lat}: no caution", isinstance(v, dict) and "Check posted signs" not in v["txt"] and v["dash"] != "8 6", repr(v)[:160])
        pg.evaluate("map.closePopup();0")
        r = pg.evaluate("testRoute([32.7930,-117.2545],[32.8125,-117.2680]).then(r=>r&&r.mi)"); pg.wait_for_timeout(500)
        steps, sub = pg.inner_text("#steps"), pg.inner_text("#sub")
        ck(f"{today} PB -> Bird Rock route found", bool(r), repr(r))
        ck(f"{today} route steps carry the caution", "Check posted signs" in steps and "Signs photographed Jan 8, 2025" in steps, steps[:300])
        ck(f"{today} route summary flags it", "posted signs may not match our data" in sub, sub)
        ck(f"{today} no Del Mar text on this route", "Nov 19, 2026" not in sub)
        b.close()
finish()
