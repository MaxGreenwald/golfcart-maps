import sys
from playwright.sync_api import sync_playwright
URL=sys.argv[1];eng=sys.argv[2];OUT=sys.argv[3] if len(sys.argv)>3 else None
fails=[];ck=lambda n,c,x="":(print("PASS" if c else "FAIL",eng,n,x),None if c else fails.append(n))
def ctr(bb):return bb["x"]+bb["width"]/2,bb["y"]+bb["height"]/2
with sync_playwright() as p:
    b=getattr(p,eng).launch();c=b.new_context(**p.devices["iPhone 13"],service_workers="block",geolocation={"latitude":32.8460,"longitude":-117.2760},permissions=["geolocation"]);pg=c.new_page();errs=[]
    pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto(URL+("&" if "?" in URL else "?")+"lat=32.8475&lon=-117.273&z=16");pg.wait_for_function("window.ready===true",timeout=120000);pg.evaluate("setSnap('collapsed')");pg.wait_for_timeout(1500)
    pg.evaluate('setMenu(true)');pg.tap("#cChg");pg.wait_for_timeout(2500)
    bb=next(e.bounding_box() for e in pg.locator(".chg").all() if (lambda q:q and 150<q["y"]<650 and 30<q["x"]<350)(e.bounding_box()))
    x,y=ctr(bb);pg.touchscreen.tap(x+12,y+12);pg.wait_for_timeout(1200)   # edge of 44px hit area
    ck("charger tap opens popup",pg.locator(".cpop").count()==1)
    if OUT:pg.screenshot(path=f"{OUT}-charger-tap.png")
    pg.evaluate("map.closePopup();0");pg.evaluate('setMenu(true)');pg.tap("#cChg");pg.wait_for_timeout(500)
    pg.evaluate("fakeLocate(32.8460,-117.2760);map.setView([32.8460,-117.2760],17);setSnap('collapsed');0");pg.wait_for_timeout(1500)
    x,y=ctr(pg.locator(".me-dot").bounding_box());pg.touchscreen.tap(x,y);pg.wait_for_timeout(1200)
    ck("location dot tap opens popup","You are here" in (pg.inner_text(".leaflet-popup") if pg.locator(".leaflet-popup").count() else ""))
    if OUT:pg.screenshot(path=f"{OUT}-location-tap.png")
    pg.locator(".leaflet-popup .pbtn",has_text="Start here").tap();pg.wait_for_timeout(500);ck("start here from dot",pg.evaluate("!!from&&from.me===true"))
    pg.evaluate("clearR();map.closePopup();0")
    pt=pg.evaluate("""(()=>{const c=map.getCenter();let best=null,bd=1e18;layer.eachLayer(g=>g.eachLayer&&g.eachLayer(l=>{if(!l.getLatLngs)return;for(const q of l.getLatLngs()){const d=map.distance(c,q);if(d<bd&&d>40){bd=d;best=q}}}));const P=map.latLngToContainerPoint(best);return [P.x,P.y]})()""")
    pg.touchscreen.tap(pt[0],pt[1]);pg.wait_for_timeout(1000);ck("road tap popup w/ report",pg.locator(".pbtn.rpt").count()==1)
    if pg.locator(".pbtn.rpt").count():
        pg.evaluate("window.NO_MAILTO=true");pg.locator(".pbtn.rpt").tap();pg.wait_for_timeout(400);ck("report form opens",pg.is_visible("#rpt"));pg.tap("#rpSend");ck("mailto built",pg.evaluate("!!window.lastReport"))
    ck("no page errors",not errs,errs[:2]);b.close()
print("RESULT",eng,"ALL PASS" if not fails else f"FAIL {fails}")
