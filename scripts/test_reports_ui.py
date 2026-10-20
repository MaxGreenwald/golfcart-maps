"""Road/hazard report form -> review queue. On a preview (URL=https://feat-reports...): the report lands as 'pending'
(checked with the reviewer key) and is then rejected to clean up. Locally: the form posts to a stub; queue down -> mailto
fallback. Routing: an unreviewed report changes nothing; a reviewed avoid steers the route but the road stays green/OK."""
from playwright.sync_api import sync_playwright
import os,sys,json,subprocess
URL=os.environ.get("URL","http://localhost:8765/");LIVE=URL.startswith("https://");fails=[]
def ck(n,c,x=""):print("PASS" if c else "FAIL",n,"" if c else str(x)[:300]);(None if c else fails.append(n))
A,B=[32.8328,-117.2713],[32.8180,-117.2700]
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page()
    pg.on("pageerror",lambda e:fails.append("js error "+str(e)))
    pg.add_init_script("localStorage.setItem('gcm-notrack','1');window.NO_MAILTO=true")
    posted=[]
    if not LIVE:
        def h(route):
            if route.request.method=="POST":posted.append(json.loads(route.request.post_data));route.fulfill(status=202,content_type="application/json",body='{"ok":true,"id":"t1","status":"pending"}')
            else:route.fulfill(status=200,content_type="application/json",body="[]")
        pg.route("**/api/report",h)
    pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    pg.evaluate("map.fire('contextmenu',{latlng:L.latLng(32.8250,-117.2700)});0");pg.click(".leaflet-popup-content .rpt")
    ck("form has hazard option",pg.locator("#rpIssue option[value=hazard]").count()==1)
    pg.select_option("#rpIssue","hazard");pg.fill("#rpNotes","[automated test] cones on the corner, call 303-555-1212")
    pg.click("#rpSend");pg.wait_for_function("window.lastReportQueued!==undefined",timeout=20000)
    q=pg.evaluate("lastReportQueued");ck("queued as pending",q and q.get("status")=="pending",q)
    ck("thank-you shown","review queue" in pg.inner_text("#rtoast"))
    if LIVE:
        out=subprocess.run(["python3","scripts/review_reports.py","list","pending"],capture_output=True,text=True).stdout
        ck("in reviewer queue",q["id"] in out and "[number removed]" in out,out[-400:])
        subprocess.run(["python3","scripts/review_reports.py","reject",q["id"],"--note","automated test cleanup"],capture_output=True)
        ck("public active list stays empty",pg.evaluate("fetch('/api/report').then(r=>r.json())")==[])
    else:
        ck("posted cleaned fields",posted and posted[0]["issue"]=="hazard" and posted[0]["region"]=="sd" and "lat" in posted[0],posted)
        pg.unroute("**/api/report");pg.route("**/api/report",lambda r:r.fulfill(status=502,body="{}"))
        pg.evaluate("map.fire('contextmenu',{latlng:L.latLng(32.8250,-117.2700)});0");pg.click(".leaflet-popup-content .rpt");pg.click("#rpSend")
        pg.wait_for_timeout(800);ck("queue down -> mailto fallback",pg.evaluate("lastReportQueued")==None and pg.evaluate("lastReport.url").startswith("mailto:"))
    # routing: steer only around reviewed avoids; legality (cls/popup) unchanged
    r0=pg.evaluate(f"testRoute({A},{B})");mid=pg.evaluate("(()=>{const l=_lastDetail.legs[Math.floor(_lastDetail.legs.length/2)];return {p:l.p[0],cls:cls(l.s),si:D.segs.indexOf(l.s)}})()")
    pg.evaluate(f"setAvoids([{{id:'x',issue:'closed',lat:{mid['p'][1]},lon:{mid['p'][0]},until:Date.now()+3600e3}}])")
    r1=pg.evaluate(f"testRoute({A},{B})")
    ck("reviewed avoid steers route",pg.evaluate(f"!_lastDetail.legs.some(l=>D.segs.indexOf(l.s)==={mid['si']})") or "reported closure" in pg.inner_text("#sub"),(r0["mi"],r1["mi"]))
    ck("legality unchanged by report",pg.evaluate(f"cls(D.segs[{mid['si']}])")==mid["cls"])
    pg.evaluate("setAvoids([])");r2=pg.evaluate(f"testRoute({A},{B})");ck("no avoids -> original route",abs(r2["mi"]-r0["mi"])<0.01)
    b.close()
print("RESULT","ALL PASS" if not fails else "FAIL "+str(fails));sys.exit(1 if fails else 0)
