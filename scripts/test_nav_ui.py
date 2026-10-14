"""Nav mode + saved places UI on an iPhone viewport: Go, banner, simulated GPS drive, reroute, arrival, mute; Home/Work/favorites/recents."""
from playwright.sync_api import sync_playwright
import os
URL=os.environ.get("URL","http://localhost:8768/");OUT=os.environ.get("SHOTS","/workspace/gcm-nav/shots");fails=[]
def ck(n,c,x=""):print("PASS" if c else "FAIL",n,str(x)[:300]);(None if c else fails.append(n))
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"],geolocation={"latitude":32.8328,"longitude":-117.2713},permissions=["geolocation"]);pg=ctx.new_page()
    pg.on("pageerror",lambda e:fails.append("js error "+str(e)))
    pg.add_init_script("window.NAV_SIM=true;window.NAV_NOANIM=true;window.NAV_ARRIVE_MS=1500;localStorage.setItem('gcm-mute','1')")
    pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    # ---- nav ----
    r=pg.evaluate("testRoute([32.8328,-117.2713],[32.8180,-117.2700])");ck("route",r and r["mi"]>0.5,r)
    ck("Go button shown",pg.is_visible("#go"))
    man=pg.evaluate("GCMNav.maneuvers(lastLegs,MODE).map(m=>m.text)");ck("maneuvers",len(man)>=3 and man[-1].startswith("Arrive"),man)
    ck("no unnamed continue steps",not any(m=="Continue straight" for m in man),man)
    pg.click("#go");pg.wait_for_timeout(300)
    ck("nav mode on",pg.evaluate("document.body.classList.contains('nav')") and pg.is_visible("#nvB"))
    ck("first announcement",len(pg.evaluate("navSaid"))==1,pg.evaluate("navSaid"))
    pts=pg.evaluate("(()=>{const L=GCMNav.line(lastLegs,MODE),o=[];for(let s=0;s<=L.total+10;s+=7){let i=1;while(i<L.cum.length-1&&L.cum[i]<s)i++;const t=Math.min(1,(s-L.cum[i-1])/((L.cum[i]-L.cum[i-1])||1)),A=L.pts[i-1],B=L.pts[i];o.push([A[1]+(B[1]-A[1])*t,A[0]+(B[0]-A[0])*t])}return o})()")
    T=[0]
    def fix(lat,lon):
        T[0]+=1000;pg.evaluate(f"navFix({lat},{lon},{T[0]},7)")
    half=len(pts)//2
    for q in pts[:half]:fix(*q)
    pg.wait_for_timeout(300);info=pg.evaluate("navInfo")
    ck("mid-route banner",info["state"]=="nav" and pg.inner_text("#nvDist")!="" and "min" in pg.inner_text("#nvRem"),(pg.inner_text("#nvDist"),pg.inner_text("#nvTxt"),pg.inner_text("#nvRem")))
    ck("ETA at cart speed",0<info["remainingSec"]/max(1,info["remaining"])*1609.34/3600 and info["remaining"]/max(1,info["remainingSec"])<11.2,(info["remaining"],info["remainingSec"]))
    ck("turn announcements",any(s.startswith("In ") for s in pg.evaluate("navSaid")),pg.evaluate("navSaid"))
    pg.screenshot(path=f"{OUT}/nav-banner-midroute.png")
    # drift ~80 m east of the route for 6 s -> reroute
    lat,lon=pts[half];said0=len(pg.evaluate("navSaid"))
    for k in range(2):fix(lat,lon+0.0009+k*0.00002)
    pg.wait_for_timeout(200);ck("off-route state before reroute",pg.evaluate("navInfo.state")=="off");pg.screenshot(path=f"{OUT}/nav-offroute.png")
    for k in range(2,6):fix(lat,lon+0.0009+k*0.00002)
    pg.wait_for_function("navInfo.state==='nav'",timeout=20000)
    said=pg.evaluate("navSaid")[said0:];ck("reroute announced",("Off route. Rerouting." in said) and ("Route updated." in said),said)
    pg.wait_for_timeout(200);pg.screenshot(path=f"{OUT}/nav-reroute.png")
    # drive the new route to the end
    pts2=pg.evaluate("(()=>{const L=NAV.L,o=[];for(let s=0;s<=L.total+10;s+=7){let i=1;while(i<L.cum.length-1&&L.cum[i]<s)i++;const t=Math.min(1,(s-L.cum[i-1])/((L.cum[i]-L.cum[i-1])||1)),A=L.pts[i-1],B=L.pts[i];o.push([A[1]+(B[1]-A[1])*t,A[0]+(B[0]-A[0])*t])}return o})()")
    for q in pts2:fix(*q)
    ck("arrived",pg.evaluate("navSaid").count("You have arrived at your destination.")==1,pg.evaluate("navSaid")[-3:])
    pg.screenshot(path=f"{OUT}/nav-arrived.png")
    pg.wait_for_timeout(1800);ck("trip ends after arrival",not pg.evaluate("document.body.classList.contains('nav')") and pg.evaluate("window.NAV")==None)
    # mute toggle
    pg.click("#go");pg.wait_for_timeout(200);m0=pg.inner_text("#nvMute");pg.click("#nvMute");m1=pg.inner_text("#nvMute");ck("mute toggle",m0!=m1 and pg.evaluate("localStorage.getItem('gcm-mute')")=="0",(m0,m1));pg.click("#nvEnd");ck("End exits",not pg.is_visible("#navui"))
    # ---- saved places ----
    pg.evaluate("resetRoute();localStorage.removeItem('gcm-places:sd');0")
    pg.click("#q");pg.wait_for_timeout(200);ck("empty saved panel",pg.is_visible("#qkHome") and "Tap ☆" in pg.inner_text("#sugg"))
    pg.fill("#q","crystal pier");pg.wait_for_timeout(3500)
    rows=pg.locator("#sugg .srow");ck("search results have stars",rows.count()>0 and rows.first.locator(".star").count()==1,rows.count())
    rows.first.locator(".star").click();pg.wait_for_timeout(200);ck("starred",len(pg.evaluate("GCMPlaces.list('sd')"))==1)
    rows.first.click();pg.wait_for_timeout(500);ck("pick adds recent",len(pg.evaluate("GCMPlaces.recents('sd')"))==1)
    # map long-press -> save place -> name it Home
    pg.evaluate("resetRoute();map.setView([32.8000,-117.2550],16,{animate:false});map.fire('contextmenu',{latlng:L.latLng(32.8000,-117.2550)});0");pg.wait_for_timeout(300)
    pg.locator(".leaflet-popup button",has_text="Save place").click();pg.wait_for_timeout(200);ck("edit dialog opens",pg.is_visible("#pe"))
    pg.fill("#peName","Beach house");pg.click("#peKind button[data-k=home]");pg.click("#peSave")
    ck("home set",(pg.evaluate("GCMPlaces.get('sd','home')") or {}).get("name")=="Beach house")
    pg.evaluate("GCMPlaces.add('sd',{name:'Office',lat:32.7157,lon:-117.1611},'work');GCMPlaces.add('sd',{name:'Taco Stand',sub:'restaurant',lat:32.7967,lon:-117.2520});GCMPlaces.addRecent('sd',{name:'Belmont Park',sub:'amusement park',lat:32.7708,lon:-117.2519});0")
    pg.click("#q");pg.wait_for_timeout(300);t=pg.inner_text("#sugg");ck("panel lists home/work/favs/recents","Beach house" in t and "Office" in t and "Taco Stand" in t and "Belmont Park" in t,t)
    pg.screenshot(path=f"{OUT}/saved-places.png")
    # rename + delete via edit
    pg.locator("#sugg .srow",has_text="Taco Stand").locator(".ed").click();pg.fill("#peName","Best Tacos");pg.click("#peSave");pg.wait_for_timeout(200)
    ck("rename",any(x["name"]=="Best Tacos" for x in pg.evaluate("GCMPlaces.list('sd')")))
    pg.click("#q");pg.locator("#sugg .srow",has_text="Best Tacos").locator(".ed").click();pg.click("#peDel");ck("delete",not any(x["name"]=="Best Tacos" for x in pg.evaluate("GCMPlaces.list('sd')")))
    # one tap to Home from GPS
    pg.evaluate("resetRoute();fakeLocate(32.8328,-117.2713);resetRoute();0");pg.click("#q");pg.wait_for_timeout(200);pg.click("#qkHome");pg.wait_for_timeout(4000)
    s=pg.evaluate("getState()");ck("one-tap home routes from GPS",s["routed"] and s["from"]["me"] and s["to"]["label"]=="Beach house",s)
    ck("Save shows saved",pg.inner_text("#save").startswith("★"))
    pg.screenshot(path=f"{OUT}/saved-home-route.png")
    ck("per-region storage",pg.evaluate("GCMPlaces.list('villages').length")==0)
    # Villages works too (golf cart mode)
    v=pg.evaluate("loadRegion('villages').then(()=>new Promise(r=>{const w=()=>window.ready?r():setTimeout(w,100);w()})).then(()=>{setMode('golf_cart');return testRoute([28.9095,-81.9745],[28.9330,-81.9590])})")
    ck("villages route",v and v["mi"]<3.5,v);pg.click("#go");pg.wait_for_timeout(300);ck("villages nav starts",pg.is_visible("#nvB"),pg.inner_text("#nvTxt"));pg.screenshot(path=f"{OUT}/nav-villages-start.png");pg.click("#nvEnd");pg.evaluate("setMode('lsv')")
print("FAILS:",fails);exit(1 if fails else 0)
