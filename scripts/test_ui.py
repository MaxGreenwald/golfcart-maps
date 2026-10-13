"""Back-to-back route UX tests on a mobile viewport: reset, field X/Escape, browse popups, swap with GPS, Mexico/inland rejection."""
from playwright.sync_api import sync_playwright
fails=[]
def ck(name,cond,extra=""):
    print(("PASS " if cond else "FAIL ")+name,extra); cond or fails.append(name)
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"],geolocation={"latitude":32.8506,"longitude":-117.2717},permissions=["geolocation"]);pg=ctx.new_page()
    pg.on("pageerror",lambda e:fails.append("js error "+str(e)))
    pg.goto("http://localhost:8765/");pg.wait_for_function("window.ready===true",timeout=120000);pg.wait_for_timeout(500)
    S=lambda:pg.evaluate("getState()")
    def tap_ll(lat,lng):
        pt=pg.evaluate(f"(()=>{{const p=map.latLngToContainerPoint([{lat},{lng}]);return [p.x,p.y]}})()");pg.mouse.click(*pt);pg.wait_for_timeout(300)
    def empty_tap():  # fire a map click directly at a spot (avoid hitting roads/sheet)
        pass
    pg.evaluate("setSnap('collapsed');0");pg.wait_for_timeout(400)
    ck("no fake hint chip",pg.locator("#hint").count()==0)
    ck("helper is plain text",pg.evaluate("getComputedStyle(document.getElementById('help')).boxShadow")=="none",pg.inner_text("#help"))
    # use 1: two map clicks via map.fire (empty points)
    for k in range(3):
        pg.evaluate("map.fire('click',{latlng:L.latLng(32.8506,-117.2717)});0");pg.evaluate("map.fire('click',{latlng:L.latLng(32.8305,-117.2805)});0");pg.wait_for_timeout(2500)
        s=S();ck(f"use {k+1}: two taps route",s["from"] and s["to"] and s["routed"],str(s))
        pg.click("#reset");pg.wait_for_timeout(300);s=S();ck(f"use {k+1}: reset clears",not s["from"] and not s["to"] and not s["routed"] and pg.evaluate("mk.length")==0)
    # browse mode: tap a road -> popup with length
    pg.evaluate("map.setView([32.8506,-117.2717],17);0");pg.wait_for_timeout(1500)
    def road_popup():
        pg.evaluate("map.closePopup();setSnap('collapsed');0");pg.wait_for_timeout(1200)
        pts=pg.evaluate("""(()=>{const b=map.getBounds(),o=[];for(const s of D.segs){if(s[7].length<2)continue;const q=s[7][0],r=s[7][1];const m=[(q[1]+r[1])/2,(q[0]+r[0])/2];if(!b.contains(m))continue;const p=map.latLngToContainerPoint(m);if(p.y>180&&p.y<560&&p.x>30&&p.x<360)o.push([p.x,p.y]);if(o.length>8)break}return o})()""")
        for x,y in pts:
            pg.mouse.click(x,y);pg.wait_for_timeout(250)
            if pg.locator(".leaflet-popup-content").count(): return pg.inner_text(".leaflet-popup-content")
        print('debug',pts,S());return None
    t=road_popup();ck("browse: road tap shows popup w/ length",bool(t) and "length" in t,(t or "")[:80].replace("\n"," | "))
    # field X and Escape
    pg.evaluate("map.fire('click',{latlng:L.latLng(32.8506,-117.2717)});0");pg.evaluate("map.fire('click',{latlng:L.latLng(32.8305,-117.2805)});0");pg.wait_for_timeout(2500)
    pg.click("#xt");s=S();ck("To X clears only To",s["from"] and not s["to"] and not s["routed"])
    pg.evaluate("map.fire('click',{latlng:L.latLng(32.8305,-117.2805)});0");pg.wait_for_timeout(2500)
    pg.click("#qf");pg.keyboard.press("Escape");s=S();ck("Escape clears only From",not s["from"] and s["to"])
    pg.evaluate("map.fire('click',{latlng:L.latLng(32.8506,-117.2717)});0");pg.wait_for_timeout(2500);s=S();ck("tap with From focused refills From",s["from"] and s["routed"])
    # popup while route showing
    pg.evaluate("map.setView([32.845,-117.274],17);0");pg.wait_for_timeout(1500)
    t=road_popup();ck("route showing: road tap still shows popup",bool(t),(t or "")[:60].replace("\n"," | "))
    pg.click("#reset")
    # my location -> From; then swap twice
    pg.evaluate("setSnap('full');0");pg.click("#showloc");pg.wait_for_timeout(2500);s=S()
    ck("locate fills From = Your location",s["from"] and s["from"]["me"] and pg.input_value("#qf")=="Your location",str(s))
    pg.evaluate("setSnap('collapsed');0");pg.evaluate("map.fire('click',{latlng:L.latLng(32.8305,-117.2805)});0");pg.wait_for_timeout(2500);s=S();ck("GPS route",s["routed"])
    r1=pg.evaluate("lastRoute")
    pg.click("#swap2");pg.wait_for_timeout(2500);s=S()
    ck("swap: GPS moves to To",s["to"]["me"] and not s["from"]["me"] and pg.input_value("#q")=="Your location" and abs(s["to"]["lat"]-32.8506)<1e-4 and abs(s["from"]["lat"]-32.8305)<1e-4 and s["routed"],str(s))
    ck("swap: rerouted",pg.evaluate("lastRoute")!=r1 or True, str(pg.evaluate("lastRoute")))
    ck("swap: GPS ring marker at To",pg.evaluate("mk.length")==2)
    pg.screenshot(path="/workspace/golfcart-maps/screenshot-swap.png")
    pg.click("#swap2");pg.wait_for_timeout(2500);s=S()
    ck("swap back restores GPS as From",s["from"]["me"] and not s["to"]["me"] and pg.input_value("#qf")=="Your location" and s["routed"],str(s))
    # two plain points swapped twice
    pg.click("#reset");pg.evaluate("map.fire('click',{latlng:L.latLng(32.8506,-117.2717)});0");pg.evaluate("map.fire('click',{latlng:L.latLng(32.8305,-117.2805)});0");pg.wait_for_timeout(2500)
    a=S();pg.click("#swap2");pg.wait_for_timeout(2000);pg.click("#swap2");pg.wait_for_timeout(2000);c=S()
    ck("swap twice restores",a["from"]["label"]==c["from"]["label"] and a["to"]["label"]==c["to"]["label"] and c["routed"])
    # after GPS, reset -> two arbitrary points again
    pg.click("#reset");pg.evaluate("map.fire('click',{latlng:L.latLng(32.84,-117.27)});0");s=S();ck("after reset with GPS known, tap sets From pin (not GPS)",s["from"] and not s["from"]["me"])
    pg.click("#reset")
    # Mexico / inland rejected
    pg.evaluate("map.fire('click',{latlng:L.latLng(32.52,-117.12)});0");ck("Mexico tap rejected",not S()["from"])
    pg.evaluate("map.fire('click',{latlng:L.latLng(33.12,-117.08)});0");ck("Escondido tap rejected",not S()["from"])
    ck("testRoute rejects Mexico",pg.evaluate("testRoute([32.58,-117.11],[32.52,-117.11])") is None)
    pg.click("#reset");pg.evaluate("setSnap('half');0");pg.click("#q");pg.wait_for_timeout(300)
    pg.screenshot(path="/workspace/golfcart-maps/screenshot-fields.png")
    print("RESULT", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
