"""Analytics in the browser (public/track.js + app.js hooks + carplay.js hook layer). Events go to a local sink
(window.GCM_TRACK_SINK), so nothing is sent anywhere.
Checks: session with UTM/referrer attribution; town_viewed; route_searched (ok + mi bucket); route_completed only
after the live location was 150+ m away and then reaches the destination; road_report_filed; CarPlay hooks tag
platform 'carplay' and reject unknown events; GPC / Do Not Track / local opt-out send nothing; no coordinates or
free text in any payload."""
from playwright.sync_api import sync_playwright
import json, os, re
from _check import ck, fail, finish
URL = os.environ.get("URL", "http://localhost:8765/").rstrip("/") + "/"
# webdriver is true under Playwright. Production treats that as e2e and does not send.
# This run is the real-user path, so force webdriver off. The e2e cases below turn it back on.
SINK = "window.GCM_TRACK_SINK=()=>{};try{Object.defineProperty(navigator,'webdriver',{configurable:true,get:()=>false})}catch(e){}"
A, B = (32.9595, -117.2655), (32.9918, -117.2717)          # Del Mar Plaza -> Fletcher Cove
ev = lambda pg: pg.evaluate("(window.__gcmSent||[]).slice()")
with sync_playwright() as p:
    launch = {}
    if os.environ.get("CHROME"):
        launch["executable_path"] = os.environ["CHROME"]
        launch["args"] = ["--no-sandbox", "--disable-dev-shm-usage"]
    b = p.chromium.launch(**launch)
    c = b.new_context(geolocation={"latitude": A[0], "longitude": A[1]}, permissions=["geolocation"], viewport={"width": 1200, "height": 900})
    pg = c.new_page(); pg.add_init_script(SINK); pg.on("pageerror", lambda e: fail("js " + str(e)))
    pg.goto(URL + "?utm_source=Nextdoor&utm_medium=paid_social&utm_campaign=dm1018", referer="https://www.google.com/search?q=golf+cart+map")
    pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(800)
    e = ev(pg); names = [x["e"] for x in e]
    s = next((x for x in e if x["e"] == "session"), None)
    ck("session first, once", names[:1] == ["session"] and names.count("session") == 1, names)
    ck("session carries UTM + first touch", bool(s) and s["p"].get("utm_source") == "nextdoor" and s["p"].get("utm_medium") == "paid_social" and s["p"].get("ft_source") == "nextdoor", s)
    ck("platform web, town sd", bool(s) and s["pl"] == "web" and s["t"] == "sd")
    ck("town_viewed", "town_viewed" in names)
    ck("install + session ids are random UUIDs", bool(s) and re.fullmatch(r"[0-9a-f-]{36}", s["i"] or "") and re.fullmatch(r"[0-9a-f-]{36}", s["s"] or ""))
    pg.evaluate("locate();0"); pg.wait_for_timeout(1500)
    pg.evaluate(f"testRoute([{A[0]},{A[1]}],[{B[0]},{B[1]}]).then(r=>r&&r.mi)"); pg.wait_for_timeout(800)
    rs = [x for x in ev(pg) if x["e"] == "route_searched"]
    ck("route_searched ok with 0.5 mi bucket", len(rs) == 1 and rs[0]["p"].get("ok") is True and isinstance(rs[0]["p"].get("mi"), (int, float)) and rs[0]["p"]["mi"] * 2 == int(rs[0]["p"]["mi"] * 2), rs)
    pg.evaluate(f"testRoute([{A[0]},{A[1]}],[{B[0]},{B[1]}]).then(r=>r&&r.mi)"); pg.wait_for_timeout(500)
    ck("same route twice within 10 min = one route_searched", len([x for x in ev(pg) if x["e"] == "route_searched"]) == 1)
    ck("no route_completed before moving", not any(x["e"] == "route_completed" for x in ev(pg)))
    c.set_geolocation({"latitude": A[0] + 0.0001, "longitude": A[1]}); pg.wait_for_timeout(1200)   # still at the start: 3.6 km from the end
    ck("no route_completed while far away", not any(x["e"] == "route_completed" for x in ev(pg)))
    c.set_geolocation({"latitude": B[0] + 0.0002, "longitude": B[1]}); pg.wait_for_timeout(1500)   # ~22 m from the destination
    done = [x for x in ev(pg) if x["e"] == "route_completed"]
    ck("route_completed once on arrival", len(done) == 1 and "mi" in done[0]["p"], done)
    c.set_geolocation({"latitude": B[0] + 0.0001, "longitude": B[1]}); pg.wait_for_timeout(1000)
    ck("arrival counted once", len([x for x in ev(pg) if x["e"] == "route_completed"]) == 1)
    # road report: open the report sheet for a road and send (mail link is intercepted, nothing leaves)
    pg.evaluate("window.open=()=>null;window._rseg={road:'Camino del Mar',hw:'primary',sp:'30 mph',src:'x',status:'OK',ll:L.latLng(32.97,-117.27)};reportRoad&&reportRoad();0"); pg.wait_for_timeout(300)
    pg.evaluate("document.getElementById('rpIssue').value='wrong_speed';try{document.getElementById('rpSend').onclick()}catch(_){};0"); pg.wait_for_timeout(300)
    rr = [x for x in ev(pg) if x["e"] == "road_report_filed"]
    ck("road_report_filed with issue enum only", len(rr) == 1 and rr[0]["p"] == {"issue": "wrong_speed"}, rr)
    # CarPlay hook layer (what CarPlaySceneDelegate.swift calls)
    r1 = pg.evaluate("GCMCarPlay.track('session')"); r2 = pg.evaluate("GCMCarPlay.track('route_started',{mi:2.4})")
    r3 = pg.evaluate("GCMCarPlay.track('route_completed',{mi:2.4})"); r4 = pg.evaluate("GCMCarPlay.track('bogus',{})")
    cp = [x for x in ev(pg) if x["pl"] == "carplay"]
    ck("CarPlay hooks return ok", r1["ok"] and r2["ok"] and r3["ok"] and not r4["ok"], [r1, r2, r3, r4])
    ck("CarPlay events tagged platform carplay", [x["e"] for x in cp][-3:] == ["session", "route_started", "route_completed"], [x["e"] for x in cp])
    pg.evaluate(f"GCMCarPlay.plan({{lat:{A[0]},lon:{A[1]}}},{{lat:{B[0]}+0.001,lon:{B[1]}}},'lsv',false).then(r=>r.ok)"); pg.wait_for_timeout(500)
    ck("CarPlay route_searched tagged carplay", any(x["e"] == "route_searched" and x["pl"] == "carplay" for x in ev(pg)))
    allp = json.dumps(ev(pg))
    ck("no coordinates or free text in any payload", not re.search(r"32\.9|117\.2|Camino|google\.com/search|golf\+cart", allp), re.findall(r".{20}(?:32\.9|117\.2|Camino).{20}", allp)[:3])
    ck("referrer host only", any(x["p"].get("ref") == "www.google.com" or x["p"].get("ref") == "google.com" for x in ev(pg) if x["e"] == "session"))
    ck("a normal browser is not marked internal", ev(pg) and all(not x.get("internal") for x in ev(pg)))
    c.close()
    for label, init in [("GPC", "Object.defineProperty(navigator,'globalPrivacyControl',{get:()=>true});"),
                        ("Do Not Track", "Object.defineProperty(navigator,'doNotTrack',{get:()=>'1'});"),
                        ("local opt-out", "localStorage.setItem('gcm-notrack','1');")]:
        c = b.new_context(); pg = c.new_page(); pg.add_init_script(SINK + init)
        pg.goto(URL); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(800)
        pg.evaluate(f"testRoute([{A[0]},{A[1]}],[{B[0]},{B[1]}]).then(r=>r&&r.mi)"); pg.evaluate("GCMCarPlay.track('route_started',{})"); pg.wait_for_timeout(300)
        ck(f"{label}: nothing sent", ev(pg) == [], ev(pg)[:2]); c.close()
    # Excluded traffic must not leave the browser. /stats also drops it if a copy is stored
    # (tests/analytics_stats.test.mjs). A normal browser still beacons.
    # Stub only sendBeacon. Replacing fetch would swallow the map's own JSON loads and window.ready would never fire.
    NET = "window.__beacons=[];navigator.sendBeacon=function(){window.__beacons.push('beacon');return true};"
    OFF = "try{Object.defineProperty(navigator,'webdriver',{configurable:true,get:()=>false})}catch(e){}"
    c = b.new_context(); pg = c.new_page(); pg.add_init_script(NET + OFF)
    pg.goto(URL); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(800)
    ck("normal browser still beacons", ev(pg) and all(not x.get("internal") for x in ev(pg)) and pg.evaluate("window.__beacons.length") > 0, pg.evaluate("window.__beacons"))
    c.close()
    for label, init, url, want in [
        ("webdriver", "", URL, "e2e"),
        ("simulator flag", "window.GCM_INTERNAL='sim';" + OFF, URL, "sim"),
        ("internal TestFlight flag", "window.GCM_INTERNAL='testflight';" + OFF, URL, "tf"),
        ("utm e2e", OFF, URL + "?utm_source=e2e&utm_medium=ci", "e2e"),
        ("stored gcm-internal", OFF + "localStorage.setItem('gcm-internal','debug');", URL, "debug"),
    ]:
        c = b.new_context(); pg = c.new_page(); pg.add_init_script(NET + init)
        pg.goto(url); pg.wait_for_function("window.ready===true", timeout=120000); pg.wait_for_timeout(800)
        pg.evaluate("GCMCarPlay.track('session')"); pg.wait_for_timeout(200)
        got = ev(pg)
        ck(f"{label}: marked {want} and not sent", bool(got) and all(x.get("internal") == want for x in got) and pg.evaluate("window.__beacons") == [], (got[:2], pg.evaluate("window.__beacons")))
        c.close()
    b.close()
finish()
