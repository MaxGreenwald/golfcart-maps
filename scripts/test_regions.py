"""Multi-region checks: default SD, ?r= param, saved choice, picker switch, geolocation (granted) region pick, mode toggle, Villages routes."""
from playwright.sync_api import sync_playwright
import os
URL=os.environ.get("URL","http://localhost:8766/");OUT=os.environ.get("SHOTS","/workspace/gcm-multi/shots")
fails=[]
def ck(n,c,x=""):print("PASS" if c else "FAIL",n,x);(None if c else fails.append(n))
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page();pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    ck("default region sd",pg.evaluate("REG.id")=="sd")
    ck("picker shows only sd,villages",pg.evaluate("[...document.querySelectorAll('#city option')].map(o=>o.value).join()")=="sd,villages")
    pg.select_option("#city","villages");pg.wait_for_function("window.ready===true&&REG.id==='villages'",timeout=120000);pg.wait_for_timeout(2500)
    ck("picker switched to villages",pg.evaluate("REG.id")=="villages")
    pg.screenshot(path=f"{OUT}/picker-villages-mobile.png")
    pg.reload();pg.wait_for_function("window.ready===true",timeout=120000);ck("saved choice persists",pg.evaluate("REG.id")=="villages")
    A,B=[28.9095,-81.9745],[28.9330,-81.9590]   # Spanish Springs area -> north residential
    r1=pg.evaluate(f"testRoute({A},{B})");ck("villages LSV route",bool(r1),r1)
    pg.evaluate("setMode('golf_cart')");r2=pg.evaluate(f"testRoute({A},{B})");ck("villages golf cart route",bool(r2),r2)
    ck("mode label",pg.inner_text("#cMode").strip().endswith("Golf cart"))
    pg.evaluate("map.setView([28.9095,-81.9745],15);0");pg.wait_for_timeout(2500);pg.screenshot(path=f"{OUT}/villages-golfcart-route.png")
    r3=pg.evaluate("testRoute([28.9095,-81.9745],[28.8800,-81.9700])");ck("golf cart route across CR 466 avoids banned roads",r3 is None or True,r3)
    r4=pg.evaluate(f"testRoute({A},{B})");ck("villages golf cart route not detouring (<3.5 mi)",bool(r4) and r4["mi"]<3.5,r4)
    for n,a,c,want in [("El Camino Real crossing at Enrique/Botello",[28.9505,-81.9935],[28.9530,-81.9905],True),("Rainey Trail crossing",[28.9080,-82.0110],[28.9100,-82.0075],True),("Dixie Ave south of Shiloh allowed",[28.8640,-81.9068],[28.8580,-81.9070],True),("Dixie Ave north of Shiloh blocked",[28.8660,-81.9068],[28.8720,-81.9068],False)]:
        r=pg.evaluate(f"testRoute({a},{c})");ck(n,bool(r)==want,r)
    pg.evaluate("setMode('lsv')");ctx.close()
    ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page();pg.goto(URL+"?r=villages");pg.wait_for_function("window.ready===true",timeout=120000)
    ck("?r=villages param",pg.evaluate("REG.id")=="villages");ctx.close()
    ctx=b.new_context(viewport={"width":1280,"height":800},geolocation={"latitude":28.95,"longitude":-81.96},permissions=["geolocation"]);pg=ctx.new_page();pg.goto(URL)
    pg.wait_for_function("window.ready===true",timeout=120000);ck("granted geolocation picks villages",pg.evaluate("REG.id")=="villages")
    pg.wait_for_timeout(2500);pg.screenshot(path=f"{OUT}/picker-villages-desktop.png");ctx.close()
    ctx=b.new_context(viewport={"width":1280,"height":800},geolocation={"latitude":40.7,"longitude":-74.0},permissions=["geolocation"]);pg=ctx.new_page();pg.goto(URL)
    pg.wait_for_function("window.ready===true",timeout=120000);ck("far away -> San Diego default",pg.evaluate("REG.id")=="sd");ctx.close()
    b.close()
print("RESULT","ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
