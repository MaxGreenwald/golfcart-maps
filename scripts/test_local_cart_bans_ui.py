"""Local golf-cart-only bans (flag 4) in the app: golf cart mode shows the road as Avoid with the ordinance link; LSV mode is unchanged."""
import os, sys
from playwright.sync_api import sync_playwright
URL = os.environ.get("URL", "http://localhost:8765/map/"); OUT = os.environ.get("SHOTS_DIR", "ci-shots/")
fails = []
def check(n, ok, d=""):
    print(("PASS " if ok else "FAIL ") + n, d)
    if not ok: fails.append(n)
CASES = [("annamaria", "Gulf Drive", "62-39"), ("chs", "Palm Boulevard", "Isle of Palms"), ("rockport", "FM", "98-133"), ("staug", "A1A Beach Boulevard", "St. Augustine Beach")]
with sync_playwright() as p:
    b = p.chromium.launch()
    for rid, road, cite in CASES:
        for veh in ("golf_cart", "lsv"):
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.goto(URL + "?r=" + rid + "&veh=" + veh); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(2500)
            pos = pg.evaluate("""async([rid,road])=>{const ix=await (await fetch('/data/'+rid+'/index.json')).json();const segs=[];
              for(const k of ix.meta.tiles)segs.push(...await (await fetch('/data/'+rid+'/tiles/'+k+'.json')).json());
              const c=segs.filter(s=>s[9]===4&&ix.names[s[0]].includes(road)&&s[7].length>=2);window._C=c;if(!c.length)return null;const s=c[Math.floor(c.length/2)];return [s[7][0][1],s[7][0][0]]}""", [rid, road])
            check(f"{rid}: flag-4 {road} present", pos is not None)
            if not pos: pg.close(); continue
            pg.evaluate("([la,lo])=>{map.setView([la,lo],18)}", pos); pg.wait_for_timeout(5000)
            hit = pg.evaluate("""()=>{const keys=new Set(window._C.map(s=>s[7][0][1].toFixed(5)+','+s[7][0][0].toFixed(5)));let hit=null;
              map.eachLayer(l=>{if(hit||!l.getLatLngs)return;const p=l.getLatLngs();if(p.length<2||p[0].lat===undefined)return;
                if(keys.has(p[0].lat.toFixed(5)+','+p[0].lng.toFixed(5))&&map.getBounds().contains(p[0]))hit=l});
              if(!hit)return null;const p=hit.getLatLngs(),m=L.latLng((p[0].lat+p[1].lat)/2,(p[0].lng+p[1].lng)/2);
              hit.fire('click',{latlng:m,originalEvent:new MouseEvent('click')});map.panTo(m);return 1}""")
            pg.wait_for_timeout(1500)
            txt = pg.inner_text(".leaflet-popup-content") if hit and pg.is_visible(".leaflet-popup-content") else ""
            check(f"{rid} {veh}: popup cites the ordinance", "No golf carts (LSVs OK)" in txt and cite in txt, txt[:200].replace("\n", " | "))
            if veh == "golf_cart": check(f"{rid} golf cart: Avoid", "golf carts not allowed on this road (local ordinance)" in txt, txt[-200:].replace("\n", " | "))
            else: check(f"{rid} LSV: not blocked by the cart-only ban", "golf carts not allowed on this road" not in txt)
            pg.screenshot(path=os.path.join(OUT, f"cartban_{rid}_{veh}.png")); pg.close()
    b.close()
print("RESULT", "ALL PASS" if not fails else "FAIL " + ", ".join(fails)); sys.exit(1 if fails else 0)
