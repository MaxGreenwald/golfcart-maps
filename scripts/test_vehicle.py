"""Vehicle toggle (plain golf cart vs LSV): chip, persistence, ?veh=, CA <=25 golf cart rule in the live map, popups, rule note,
routes for golf carts never use a road posted over 25 in CA, HI/ME golf carts cart-paths only. Uses public/roadrule.js via the page."""
from playwright.sync_api import sync_playwright
import os
URL=os.environ.get("URL","http://localhost:8765/");OUT=os.environ.get("SHOTS","/tmp/")
fails=[]
def ck(n,c,x=""):print(("PASS " if c else "FAIL ")+n,x);c or fails.append(n)
FIND="""(async()=>{await ensure(33.12,-117.36,33.17,-117.30);const s=D.segs.find(x=>D.names[x[0]]==='Carlsbad Boulevard'&&x[2]===35&&'tvm'.includes(x[3])&&x[7][0][1]>33.13&&x[7][0][1]<33.16);return s?[s[7][0],cls(s)]:null})()"""
CLS="""(async()=>{await ensure(33.12,-117.36,33.17,-117.30);return cls(D.segs.find(x=>D.names[x[0]]==='Carlsbad Boulevard'&&x[2]===35&&'tvm'.includes(x[3])&&x[7][0][1]>33.13&&x[7][0][1]<33.16))})()"""
POP="""(async(q)=>{map.setView([q[1],q[0]],17);await new Promise(r=>setTimeout(r,1400));let pl=null;layer.eachLayer(g=>{(g.eachLayer?g:{eachLayer:f=>f(g)}).eachLayer(l=>{const A=l.getLatLngs&&l.getLatLngs(),ll=A&&A[0];if(ll&&Math.abs(ll.lat-q[1])<1e-6&&Math.abs(ll.lng-q[0])<1e-6&&!pl)pl=l})});
 if(!pl)return 'NO LINE';pl.fire('click',{latlng:L.latLng(q[1],q[0])});await new Promise(r=>setTimeout(r,250));return (document.querySelector('.leaflet-popup-content')||{}).innerText||''})"""
ROUTE="(window._lastDetail=null,testRoute([33.1595,-117.3505],[33.1335,-117.3360]).then(r=>({mi:r&&r.mi,max:window._lastDetail?Math.max(0,...window._lastDetail.legs.filter(l=>l.s[3]!=='c').map(l=>l.s[2]==null?999:l.s[2])):null})))"
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page();pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    ck("default vehicle is LSV (no change for existing users)",pg.evaluate("MODE")=="lsv")
    ck("chip shows LSV",pg.get_attribute("#cVeh","aria-label")=="Vehicle type: LSV" and "🚙" in pg.inner_text("#cVeh"),pg.inner_text("#cVeh"))
    ck("rule note names LSVs",pg.inner_text("#rnote").startswith("California, LSVs: roads posted ≤35 mph"),pg.inner_text("#rnote"))
    f=pg.evaluate(FIND);ck("found a 35 mph Carlsbad Blvd segment",bool(f),f)
    ck("LSV: 35 mph road is OK",f and f[1]!=3)
    t=pg.evaluate(POP,f[0]);ck("LSV popup: OK for LSVs, not for golf carts",("OK for LSVs" in t) and ("not for golf carts: only roads ≤25 mph" in t),t[:200])
    ck("no 'carts & LSVs' wording in popup",'carts & LSVs' not in t)
    r=pg.evaluate(ROUTE);ck("LSV route found",bool(r["mi"]),r)
    pg.screenshot(path=OUT+"veh-lsv-popup.png")
    pg.click("#cVeh");pg.wait_for_function("window.ready===true&&MODE==='golf_cart'&&REG&&REG.id==='sd'",timeout=120000);pg.wait_for_timeout(1500)
    ck("chip switched to golf cart",pg.get_attribute("#cVeh","aria-label")=="Vehicle type: golf cart" and "🛺" in pg.inner_text("#cVeh"))
    ck("rule note: golf carts <=25 (CVC 21716 in title)",pg.inner_text("#rnote").startswith("California, golf carts: roads posted ≤25 mph") and "21716" in pg.get_attribute("#rnote","title"),pg.inner_text("#rnote"))
    ck("legend says Posted ≤25 / 26+ avoid",pg.inner_text("#lgOk")=="Posted ≤25" and pg.inner_text("#lgNo").startswith("26+"))
    ck("golf cart: same 35 mph road is Avoid",pg.evaluate(CLS)==3)
    t=pg.evaluate(POP,f[0]);ck("golf cart popup: Avoid, OK for LSVs",("Avoid: 26+ mph or major road (OK for LSVs)" in t),t[:200])
    pg.screenshot(path=OUT+"veh-cart-popup.png")
    r=pg.evaluate(ROUTE);ck("golf cart route never uses a road posted over 25",r["mi"] is None or (r["max"] is not None and r["max"]<=25),r)
    r=pg.evaluate(ROUTE.replace("[33.1595,-117.3505],[33.1335,-117.3360]","[32.797,-117.252],[32.806,-117.256]"));ck("golf cart route in Pacific Beach found, all roads <=25",bool(r["mi"]) and r["max"]<=25,r)
    pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000);ck("vehicle choice persists",pg.evaluate("MODE")=="golf_cart")
    ctx.close()
    ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page();pg.goto(URL+"?r=oob&veh=golf_cart");pg.wait_for_function("window.ready===true",timeout=120000)
    ck("?veh= param + Maine golf carts: cart paths only",pg.evaluate("MODE")=="golf_cart" and "cart paths only" in pg.inner_text("#rnote"),pg.inner_text("#rnote"))
    ck("Maine golf cart: every road Avoid",pg.evaluate("D.segs.filter(s=>s[3]!=='c').every(s=>cls(s)===3)"))
    pg.click("#cVeh");pg.wait_for_function("window.ready===true&&MODE==='lsv'",timeout=120000)
    ck("Maine LSV: roads posted ≤35 OK",pg.evaluate("D.segs.some(s=>s[2]===35&&cls(s)!==3)") and "street-legal LSVs" in pg.inner_text("#rnote"),pg.inner_text("#rnote"))
    ctx.close();b.close()
print("RESULT","ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
