"""Saved places UI (iPhone viewport): save a route destination, make it Home, Home shows first on focus, one-tap route,
long-press drops a pin menu, share falls back to a link box when Web Share and clipboard are unavailable, ?pin= deep link."""
from playwright.sync_api import sync_playwright
import os,sys
URL=os.environ.get("URL","http://localhost:8765/");fails=[]
def ck(n,c,x=""):print("PASS" if c else "FAIL",n,"" if c else str(x)[:300]);(None if c else fails.append(n))
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page()
    pg.on("pageerror",lambda e:fails.append("js error "+str(e)))
    pg.add_init_script("localStorage.setItem('gcm-notrack','1');try{delete Navigator.prototype.share}catch(_){};Object.defineProperty(navigator,'clipboard',{value:{writeText:()=>Promise.reject(new Error('no'))}})")
    pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    r=pg.evaluate("testRoute([32.8328,-117.2713],[32.8180,-117.2700])");ck("route",bool(r))
    ck("Save button",pg.is_visible("#save") and "Save" in pg.inner_text("#save"))
    pg.click("#save");pg.wait_for_timeout(200);ck("name dialog",pg.is_visible("#pe"))
    pg.fill("#peName","Beach house");pg.click("#peKind button[data-k=home]");pg.click("#peSave")
    ck("saved as Home",pg.evaluate("GCMPlaces.get('sd','home').name")=="Beach house")
    ck("button shows saved","Saved" in pg.inner_text("#save"))
    pg.evaluate("resetRoute()");pg.click("#q");pg.wait_for_timeout(200)
    ck("Home first in list",pg.is_visible("#qkHome") and "Beach house" in pg.inner_text("#qkHome"))
    if os.environ.get("SHOT"):pg.screenshot(path="shots/places-list.png")
    pg.evaluate("from=null");pg.evaluate("window.__f=1")
    pg.evaluate("(()=>{window._x=1})()")
    pg.click("#qf");pg.wait_for_timeout(100);pg.evaluate("setField('from',{ll:L.latLng(32.8328,-117.2713),label:'A'})")
    pg.click("#q");pg.wait_for_timeout(200);pg.click("#qkHome");pg.wait_for_function("getState().routed",timeout=20000)
    ck("one-tap Home routes",pg.evaluate("getState().routed"))
    # long-press (contextmenu) drop-pin menu
    pg.evaluate("resetRoute();map.fire('contextmenu',{latlng:L.latLng(32.80,-117.255)});0");pg.wait_for_timeout(200)
    t=pg.inner_text(".leaflet-popup-content");ck("pin menu",all(k in t for k in ["Dropped pin","Go here","Save","Share","Report"]),t)
    pg.click(".leaflet-popup-content button:has-text('Share')");pg.wait_for_timeout(300)
    ck("link fallback box",pg.is_visible("#shBox") and "pin=Dropped+pin" in pg.input_value("#shLink"),pg.input_value("#shLink") if pg.is_visible("#shBox") else "")
    link=pg.input_value("#shLink");pg.click("#shClose")
    pg.evaluate("map.fire('contextmenu',{latlng:L.latLng(32.80,-117.255)});0");pg.click(".leaflet-popup-content button:has-text('Go here')");pg.wait_for_timeout(200)
    ck("drop pin sets destination",pg.evaluate("getState().to!=null"))
    # deep link sets destination
    q=link.split("?",1)[1];pg.goto(URL+"?"+q);pg.wait_for_function("window.ready===true",timeout=120000);pg.wait_for_timeout(300)
    ck("?pin= deep link",pg.input_value("#q")=="Dropped pin",pg.input_value("#q"))
    ck("persists across sessions",pg.evaluate("GCMPlaces.get('sd','home')&&GCMPlaces.get('sd','home').name")=="Beach house")
    b.close()
print("RESULT","ALL PASS" if not fails else "FAIL "+str(fails));sys.exit(1 if fails else 0)
