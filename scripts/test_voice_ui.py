"""Voice turn-by-turn on an iPhone viewport: Go, banner, speed sign, heading dot, simulated drive, reroute, arrival,
mute remembered across reloads, heading-up toggle in Settings."""
from playwright.sync_api import sync_playwright
import os,sys
URL=os.environ.get("URL","http://localhost:8765/");fails=[]
def ck(n,c,x=""):print("PASS" if c else "FAIL",n,"" if c else str(x)[:300]);(None if c else fails.append(n))
DRIVE="(L=>{const o=[];for(let s=0;s<=L.total+10;s+=7){let i=1;while(i<L.cum.length-1&&L.cum[i]<s)i++;const t=Math.min(1,(s-L.cum[i-1])/((L.cum[i]-L.cum[i-1])||1)),A=L.pts[i-1],B=L.pts[i];o.push([A[1]+(B[1]-A[1])*t,A[0]+(B[0]-A[0])*t])}return o})"
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"],geolocation={"latitude":32.8328,"longitude":-117.2713},permissions=["geolocation"]);pg=ctx.new_page()
    pg.on("pageerror",lambda e:fails.append("js error "+str(e)))
    pg.add_init_script("window.NAV_SIM=true;window.NAV_NOANIM=true;window.NAV_ARRIVE_MS=1500;localStorage.setItem('gcm-notrack','1')")
    pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    pg.evaluate("setMute(true)")
    r=pg.evaluate("testRoute([32.8328,-117.2713],[32.8180,-117.2700])");ck("route",r and r["mi"]>0.5,r)
    ck("Go button shown",pg.is_visible("#go"))
    pg.click("#go");pg.wait_for_timeout(300)
    ck("nav mode on",pg.evaluate("document.body.classList.contains('nav')") and pg.is_visible("#nvB"))
    ck("first announcement",len(pg.evaluate("navSaid"))==1,pg.evaluate("navSaid"))
    pts=pg.evaluate(DRIVE+"(GCMNav.line(lastLegs,'lsv'))");T=[0]
    def fix(lat,lon,h='undefined'):
        T[0]+=1000;pg.evaluate(f"navFix({lat},{lon},{T[0]},7,{h})")
    half=len(pts)//2
    for q in pts[:half]:fix(*q)
    pg.wait_for_timeout(300);info=pg.evaluate("navInfo")
    ck("mid-route banner",info["state"]=="nav" and pg.inner_text("#nvDist")!="" and "min" in pg.inner_text("#nvRem"))
    ck("speed-limit sign",pg.is_visible("#nvLim") and pg.inner_text("#nvLimN").strip() in ("?",str(info["limit"])),(pg.inner_text("#nvLimN"),info["limit"]))
    ck("heading indicator",pg.evaluate("!!document.querySelector('.hdgb')") and pg.evaluate("navHeading")!=None)
    ck("turn announcements",any(s.startswith("In ") for s in pg.evaluate("navSaid")),pg.evaluate("navSaid"))
    if os.environ.get("SHOT"):pg.screenshot(path="shots/voice-nav.png")
    # heading-up rotates the map; north-up resets
    pg.evaluate("setHeadUp(true)");fix(*pts[half],90);pg.wait_for_timeout(200)
    ck("heading-up rotates map","rotate(-90deg)" in pg.evaluate("document.getElementById('map').style.transform"),pg.evaluate("document.getElementById('map').style.transform"))
    pg.evaluate("setHeadUp(false)");ck("north-up resets",pg.evaluate("document.getElementById('map').style.transform")=="")
    lat,lon=pts[half];said0=len(pg.evaluate("navSaid"))
    for k in range(6):fix(lat,lon+0.0009+k*0.00002)
    pg.wait_for_function("navInfo.state==='nav'",timeout=20000)
    said=pg.evaluate("navSaid")[said0:];ck("reroute announced","Off route. Rerouting." in said and "Route updated." in said,said)
    pts2=pg.evaluate(DRIVE+"(NAV.L)")
    for q in pts2:fix(*q)
    ck("arrived","You have arrived at your destination." in pg.evaluate("navSaid"))
    pg.wait_for_timeout(2200);ck("nav ends after arrival",not pg.evaluate("document.body.classList.contains('nav')"))
    # mute + heading mode remembered between sessions; toggles live in Settings
    pg.evaluate("setHeadUp(true)");pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    ck("mute remembered",pg.evaluate("localStorage.getItem('gcm-mute')")=="1" and not pg.is_checked("#setVoice"))
    ck("heading-up remembered",pg.is_checked("#setHup"))
    pg.evaluate("setMute(false);setHeadUp(false)");ck("unmute saved",pg.evaluate("localStorage.getItem('gcm-mute')")=="0")
    b.close()
print("RESULT","ALL PASS" if not fails else "FAIL "+str(fails));sys.exit(1 if fails else 0)
