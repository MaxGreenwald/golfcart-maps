"""Trusted OSM ('o') in the app: drawn and routed exactly like the OSM tag it relabels ('t'), never says "verified",
and the popup says "OpenStreetMap, matches nearby sign"."""
import os, sys
from playwright.sync_api import sync_playwright
URL = os.environ.get("URL", "http://localhost:8765/map/")
fails = []
def check(n, ok, d=""):
    print(("PASS " if ok else "FAIL ") + n, d)
    if not ok: fails.append(n)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(URL + "occoast"); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(3000)
    r = pg.evaluate("""(async()=>{const ix=await (await fetch('/data/ocoast/index.json')).json();const segs=[];
      for(const k of ix.meta.tiles)segs.push(...await (await fetch('/data/ocoast/tiles/'+k+'.json')).json());window._OS=segs;let n=0,bad=0;
      for(const s of segs){if(s[3]!=='o')continue;n++;const t=s.slice();t[3]='t';
      for(const lenient of [false,true])if(GCMRule.cls(s,RULE,lenient)!==GCMRule.cls(t,RULE,lenient))bad++}return [n,bad]})()""")
    check("o segments present", r[0] > 0, str(r))
    check("o segments draw/route exactly like t", r[1] == 0, str(r))
    pos = pg.evaluate("(()=>{const s=window._OS.filter(s=>s[3]==='o'&&s[1].startsWith('secondary'))[5];const a=s[7][0];return [a[1],a[0]]})()")
    check("found an o segment on the map", pos is not None)
    if pos:
        pg.evaluate("([la,lo])=>map.setView([la,lo],17)", pos); pg.wait_for_timeout(6000)
        hit = pg.evaluate("""()=>{const keys=new Set(window._OS.filter(s=>s[3]==='o').map(s=>s[7][0][1].toFixed(5)+','+s[7][0][0].toFixed(5)));let hit=null;
          map.eachLayer(l=>{if(hit||!l.getLatLngs)return;const p=l.getLatLngs();if(p.length<2||p[0].lat===undefined)return;
            if(keys.has(p[0].lat.toFixed(5)+','+p[0].lng.toFixed(5))&&map.getBounds().contains(p[0]))hit=l});
          if(!hit)return null;const p=hit.getLatLngs(),m=L.latLng((p[0].lat+p[1].lat)/2,(p[0].lng+p[1].lng)/2);
          hit.fire('click',{latlng:m,originalEvent:new MouseEvent('click')});map.panTo(m);return [m.lat,m.lng]}""")
        check("o road drawn on the map", hit is not None, str(hit)); pg.wait_for_timeout(1500)
        txt = pg.inner_text(".leaflet-popup-content") if pg.is_visible(".leaflet-popup-content") else ""
        check("popup: OpenStreetMap, matches nearby sign", "OpenStreetMap, matches nearby sign" in txt, txt[:160].replace("\n", " | "))
        check("popup never says verified", "erified" not in txt, txt[:160].replace("\n", " | "))
        pg.screenshot(path="ci-shots/trusted_osm_popup.png")
    b.close()
print("RESULT", "ALL PASS" if not fails else "FAIL " + ", ".join(fails)); sys.exit(1 if fails else 0)
