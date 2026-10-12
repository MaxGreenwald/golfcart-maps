from playwright.sync_api import sync_playwright
R={"cove_windansea":([32.8506,-117.2717],[32.8305,-117.2805]),"delmar15_solana":([32.9598,-117.2655],[32.9932,-117.2713])}
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page()
    pg.goto("http://localhost:8765/");pg.wait_for_function("window.ready===true",timeout=120000)
    pg.wait_for_timeout(800);print("initial snap",pg.evaluate("getSnap()"));pg.screenshot(path="/workspace/golfcart-maps/screenshot-open.png")
    cdp=ctx.new_cdp_session(pg)
    def drag(y0,y1):
        cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":195,"y":y0}]})
        for i in range(1,11): cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":195,"y":y0+(y1-y0)*i/10}]});pg.wait_for_timeout(30)
        cdp.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]});pg.wait_for_timeout(400)
    top=pg.evaluate("document.getElementById('shead').getBoundingClientRect().top")
    drag(top+10,top+700);print("after swipe down",pg.evaluate("getSnap()"))
    top=pg.evaluate("document.getElementById('shead').getBoundingClientRect().top")
    drag(top+10,top-300);print("after swipe up",pg.evaluate("getSnap()"))
    top=pg.evaluate("document.getElementById('shead').getBoundingClientRect().top")
    pg.tap(f"#shead");pg.wait_for_timeout(400);print("after tap",pg.evaluate("getSnap()"))
    for k,(a,c) in R.items():
        for rk in (False,True): print(k,"risky" if rk else "legal",pg.evaluate(f"testRoute({a},{c},{str(rk).lower()})"))
    pg.evaluate("setRisky(false)");print(pg.evaluate("testRoute([32.8506,-117.2717],[32.8305,-117.2805])"))
    pg.evaluate("map.fitBounds([[32.826,-117.29],[32.853,-117.262]]);0");pg.wait_for_timeout(5000)
    print("route snap",pg.evaluate("getSnap()"))
    pg.screenshot(path="/workspace/golfcart-maps/screenshot.png");b.close()
# geolocation test
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"],geolocation={"latitude":32.8471,"longitude":-117.2742},permissions=["geolocation"]);pg=ctx.new_page()
    pg.goto("http://localhost:8765/");pg.wait_for_function("window.ready===true",timeout=120000);pg.wait_for_timeout(500)
    print("loc fab visible",pg.is_visible("#loc"),"prompt",pg.is_visible("#showloc"))
    pg.click("#showloc");pg.wait_for_timeout(2500)
    pg.mouse.click(150,250);pg.wait_for_timeout(2500);print("title",pg.inner_text("#title"))
    pg.screenshot(path="/workspace/golfcart-maps/screenshot-locate.png");b.close()
