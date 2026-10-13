from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch()
    for name,kw in [("mobile",p.devices["iPhone 13"]),("desktop",{"viewport":{"width":1440,"height":900}})]:
        pg=b.new_page(**kw);pg.goto("http://localhost:8765/");pg.wait_for_function("window.ready===true",timeout=120000);pg.wait_for_timeout(800)
        r=lambda s:pg.evaluate(f"(()=>{{const r=document.querySelector('{s}').getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]}})()")
        vis=lambda:pg.evaluate("innerHeight-document.getElementById('sheet').getBoundingClientRect().top")
        print(name,"snap",pg.evaluate("getSnap()"),"sheet",r('#sheet'),"visible",vis(),"top",r('#top'),"loc",r('#loc'),"details open",pg.evaluate("more.open"))
        pg.screenshot(path=f"/workspace/golfcart-maps/screenshot-{name}.png")
        pg.evaluate("testRoute([32.8506,-117.2717],[32.8305,-117.2805]).then(()=>0)");pg.wait_for_timeout(3000)
        pg.evaluate("setSnap('full');0");pg.wait_for_timeout(500);print(" full visible",vis(),"sbody scroll",pg.evaluate("[sbody.scrollHeight,sbody.clientHeight]"))
        pg.screenshot(path=f"/workspace/golfcart-maps/screenshot-{name}-route.png")
        pg.evaluate("setSnap('collapsed');0");pg.wait_for_timeout(500);print(" collapsed visible",vis())
