"""Battery on arrival + multiple stops (iPhone viewport): arrival/back-home %, D5 4+2 preset, full-cart estimate label,
charge-overnight tip only when low, add/remove stops, stop route longer than direct and legal."""
from playwright.sync_api import sync_playwright
import os,sys
URL=os.environ.get("URL","http://localhost:8765/");fails=[]
def ck(n,c,x=""):print("PASS" if c else "FAIL",n,"" if c else str(x)[:300]);(None if c else fails.append(n))
A,B=[32.8328,-117.2713],[32.8180,-117.2700]
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page()
    pg.on("pageerror",lambda e:fails.append("js error "+str(e)))
    pg.add_init_script("localStorage.setItem('gcm-notrack','1')")
    pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    r=pg.evaluate(f"testRoute({A},{B})");t=pg.inner_text("#range")
    ck("arrival line","Battery on arrival" in t and "back home" in t,t)
    ar=pg.evaluate("_arrival");ck("arrival math",ar["one"]==round(100-r["mi"]/30*100) and ar["rt"]==round(100-r["rt"]/30*100),(ar,r))
    ck("no tip when charged","overnight" not in t)
    pg.click("#range summary");pg.select_option("#rgPf","d5_42");pg.wait_for_timeout(200);t=pg.inner_text("#range")
    ck("D5 preset + source","Evolution D5 4+2" in t and "Beach Mode Rentals" in t,t)
    ck("range input locked to preset",pg.is_disabled("#rgMi"))
    pg.check("#rgFull");pg.wait_for_timeout(200);t=pg.inner_text("#range")
    ck("full cart labeled estimate","estimate, not a measured number" in t and "26.4 mi" in t,t)
    pg.fill("#rgBat","20");pg.dispatch_event("#rgBat","change");pg.wait_for_timeout(200);t=pg.inner_text("#range")
    ck("charge tip when low","plug your cart in overnight" in t,t)
    if os.environ.get("SHOT"):pg.evaluate("setSnap('full')");pg.wait_for_timeout(400);pg.screenshot(path="shots/battery.png")
    pg.evaluate("localStorage.removeItem('gcm-range')")
    ck("+ Stop shown",pg.is_visible("#addStop"))
    pg.click("#addStop");pg.evaluate("setSnap('collapsed')")
    pg.evaluate("setPt(L.latLng(32.8255,-117.2560),'Stop A')");pg.wait_for_function("lastRoute&&lastRoute.stops===1",timeout=20000)
    r2=pg.evaluate("lastRoute");ck("stop route longer",r2["mi"]>r["mi"]+0.2,(r["mi"],r2["mi"]))
    ck("stop route legal",pg.evaluate("_lastDetail.legs.every(l=>!l.f)"))
    ck("stop listed","Stop A" in pg.inner_text("#stops") and "with 1 stop" in pg.inner_text("#range"))
    pg.evaluate("removeStop(0)");pg.wait_for_function("lastRoute.stops===0",timeout=20000);ck("stop removed",abs(pg.evaluate("lastRoute.mi")-r["mi"])<0.05)
    for i in range(4):pg.evaluate(f"addStop({{ll:L.latLng(32.826+{i}*0.001,-117.265),label:'S{i}'}})")
    pg.wait_for_timeout(800);ck("max 3 stops",pg.evaluate("getStops().length")==3 and not pg.is_visible("#addStop"))
    pg.evaluate("resetRoute()");ck("reset clears stops",pg.evaluate("getStops().length")==0)
    b.close()
print("RESULT","ALL PASS" if not fails else "FAIL "+str(fails));sys.exit(1 if fails else 0)
