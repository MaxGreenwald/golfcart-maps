"""Street View check sources (Drive photo links, e.g. 'photo SD-B2-064.jpg') show '📷 Street View check' in the road popup,
never '📰 local report'. Real local reports and DOT/city sources keep their own labels."""
import os, sys
from playwright.sync_api import sync_playwright
URL = os.environ.get("URL", "http://localhost:8765/map/")
fails = []
def check(n, ok, d=""):
    print(("PASS " if ok else "FAIL ") + n, d)
    if not ok: fails.append(n)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(URL + "sd"); pg.wait_for_function("window.ready===true", timeout=120000)
    k = lambda u, t: pg.evaluate("([u,t])=>{const o=D.sources;D.sources=[[u,t]];const r=srcKind([0,'x',35,'v',0,0,0,[],0]);D.sources=o;return r}", [u, t])
    sv = k("https://drive.google.com/file/d/1rCLhHLOzy22Epqm53SLFkf2oZl9Oj_hL/view?usp=drivesdk", "posted sign, Street View check (RG), photo SD-B2-064.jpg")
    check("batch 2 Drive photo -> Street View check", sv == "📷 Street View check", sv)
    check("bare photo id -> Street View check", k("https://drive.google.com/file/d/x/view", "photo VILLAGES-B2-002.jpg") == "📷 Street View check")
    check("google maps pano still Street View", k("https://www.google.com/maps/@?api=1&map_action=pano", "sign") == "📷 Street View check")
    check("news link stays local report", k("https://www.example-news.com/a", "Town council article") == "📰 local report")
    check("DOT stays DOT", k("https://gis-fdot.opendata.arcgis.com/x", "FDOT Maximum Speed Limit (TDA)") == "📄 state DOT data")
    pg.evaluate("map.setView([32.75913,-117.18300],17);0"); pg.wait_for_timeout(4000)
    x, y = pg.evaluate("(()=>{const q=map.latLngToContainerPoint([32.75913,-117.18300]);const r=map.getContainer().getBoundingClientRect();return [q.x+r.left,q.y+r.top]})()")
    pg.mouse.click(x, y); pg.wait_for_timeout(1500)
    txt = pg.inner_text(".leaflet-popup-content") if pg.is_visible(".leaflet-popup-content") else ""
    check("Hotel Circle South popup: 35 mph + Street View check", "Hotel Circle South" in txt and "35 mph" in txt and "Street View check" in txt and "local report" not in txt, txt[:120].replace("\n", " | "))
    b.close()
print("RESULT", "ALL PASS" if not fails else "FAIL " + ", ".join(fails)); sys.exit(1 if fails else 0)
