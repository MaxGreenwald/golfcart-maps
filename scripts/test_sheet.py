from playwright.sync_api import sync_playwright
import os
from _check import finish
URL=os.environ.get("URL","http://localhost:8765/")
with sync_playwright() as p:
    b=p.webkit.launch();ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page()
    pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000);pg.wait_for_timeout(800)
    vis=lambda:pg.evaluate("Math.round((innerHeight-document.getElementById('sheet').getBoundingClientRect().top)/innerHeight*100)")
    print("load",pg.evaluate("getSnap()"),vis(),"% visible")
    pg.screenshot(path="/workspace/golfcart-maps/screenshot-open.png")
    def drag(dy):
        r=pg.evaluate("(()=>{const r=document.getElementById('shead').getBoundingClientRect();return [r.left+100,r.top+30]})()")
        x,y=r
        js=f"""(async()=>{{const el=document.getElementById('shead');const mk=(t,y)=>new PointerEvent(t,{{pointerId:1,pointerType:'touch',clientX:{x},clientY:y,bubbles:true,cancelable:true,isPrimary:true}});
        el.dispatchEvent(mk('pointerdown',{y}));for(let i=1;i<=10;i++){{await new Promise(r=>setTimeout(r,16));el.dispatchEvent(mk('pointermove',{y}+{dy}*i/10))}}el.dispatchEvent(mk('pointerup',{y}+{dy}))}})()"""
        pg.evaluate(js);pg.wait_for_timeout(500)
    drag(400);print("swipe down",pg.evaluate("getSnap()"),vis())
    drag(-150);print("swipe up",pg.evaluate("getSnap()"),vis())
    pg.tap("#chev");pg.wait_for_timeout(400);print("chevron",pg.evaluate("getSnap()"),vis())
    pg.tap(".grab");pg.wait_for_timeout(400);print("tap handle",pg.evaluate("getSnap()"),vis())
    my=pg.evaluate("Math.round((Math.max($('top').getBoundingClientRect().bottom,$('chips').getBoundingClientRect().bottom,($('rnote')||$('top')).getBoundingClientRect().bottom)+$('sheet').getBoundingClientRect().top)/2)");pg.tap("#map",position={"x":200,"y":my});pg.wait_for_timeout(400);print("tap map",pg.evaluate("getSnap()"),vis())
    print(pg.evaluate("testRoute([32.8506,-117.2717],[32.8305,-117.2805])"),"after route",pg.evaluate("getSnap()"),vis())
    pg.evaluate("map.fitBounds([[32.826,-117.29],[32.853,-117.262]]);0");pg.wait_for_timeout(4000)
    pg.screenshot(path="/workspace/golfcart-maps/screenshot.png");b.close()
finish()
