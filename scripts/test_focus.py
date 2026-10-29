"""After routing, the map flies to the START at z16, centered in the visible area (not under the sheet/card)."""
from playwright.sync_api import sync_playwright
import os
from _check import ck, finish
URL=os.environ.get("URL","http://localhost:8765/")
with sync_playwright() as p:
    b=p.chromium.launch()
    for name,kw in [("mobile",p.devices["iPhone 13"]),("desktop",{"viewport":{"width":1440,"height":900}})]:
        pg=b.new_page(**kw);pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
        for a,c in [([32.8506,-117.2717],[32.8305,-117.2805]),([32.6990,-117.1696],[32.6828,-117.1789])]:
            pg.evaluate("map.setView([32.9,-117.25],12);0");pg.wait_for_timeout(500)
            pg.evaluate(f"testRoute({a},{c}).then(()=>0)");pg.wait_for_timeout(2000)
            r=pg.evaluate(f"(()=>{{const p=map.latLngToContainerPoint({a}),t=document.getElementById('top').getBoundingClientRect(),s=document.getElementById('sheet').getBoundingClientRect();return {{z:map.getZoom(),x:Math.round(p.x),y:Math.round(p.y),topB:Math.round(t.bottom),sheetT:Math.round(s.top),cardR:Math.round(s.right)}}}})()")
            ok=r['z']==16 and r['y']>r['topB'] and (r['y']<r['sheetT'] if name=="mobile" else r['x']>r['cardR'])
            ck(f"{name} {a}", ok, r)
        pg.screenshot(path=f"/workspace/golfcart-maps/screenshot-focus-{name}.png")
    finish()
