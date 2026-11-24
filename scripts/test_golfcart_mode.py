"""Settings > Golf cart mode (25 mph roads only). Off (default): street-legal LSV, roads posted 35 mph or less.
On: golf carts, roads posted 25 mph or less in every state, including Texas where state law alone would allow 35.
Checks the default, the stored-value migration, rendering and routing at 35 vs 25 in Galveston (TX), low-confidence
roads drawn dotted green (never yellow) with a Confidence: Low popup, and the legend labels.
Screenshots go to $SHOTS (default /tmp/)."""
from playwright.sync_api import sync_playwright
import os
from _check import ck, finish
URL=os.environ.get("URL","http://localhost:8765/");OUT=os.environ.get("SHOTS","/tmp/")
GAL="?r=galveston&lat=29.2990&lon=-94.7900&z=16"
COR="?r=sd&lat=32.6835&lon=-117.1780&z=15"
SEG="""(async(q)=>{await ensure(29.27,-94.81,29.32,-94.76);const s=D.segs.find(x=>D.names[x[0]]===q[0]&&x[2]===q[1]&&x[3]===q[2]&&(!q[3]||x[1]===q[3]));return s?{p:[s[7][0],s[7][s[7].length-1]],c:cls(s),unk:unk(s)}:null})"""
LINE="""(async(e)=>{const q=e[0],z=e[1];map.setView([q[1],q[0]],17);await new Promise(r=>setTimeout(r,1400));let pl=null;const near=(ll,c)=>ll&&Math.abs(ll.lat-c[1])<1e-6&&Math.abs(ll.lng-c[0])<1e-6;layer.eachLayer(g=>{(g.eachLayer?g:{eachLayer:f=>f(g)}).eachLayer(l=>{const A=l.getLatLngs&&l.getLatLngs();if(A&&near(A[0],q)&&near(A[A.length-1],z)&&!pl)pl=l})});
 if(!pl)return null;const o={color:pl.options.color,dash:pl.options.dashArray||''};const m=pl.getLatLngs()[Math.floor(pl.getLatLngs().length/2)];pl.fire('click',{latlng:m});await new Promise(r=>setTimeout(r,300));o.txt=(document.querySelector('.leaflet-popup-content')||{}).innerText||'';return o})"""
YELLOW="""(()=>{let n=0,all=0;layer.eachLayer(g=>{(g.eachLayer?g:{eachLayer:f=>f(g)}).eachLayer(l=>{all++;const c=(l.options.color||'').toLowerCase();if(c==='#e0a800'||c==='#ffc400')n++})});return {n,all}})()"""
ROUTE="(window._lastDetail=null,testRoute(%s,%s).then(r=>({mi:r&&r.mi,max:window._lastDetail?Math.max(0,...window._lastDetail.legs.filter(l=>l.s[3]!=='c').map(l=>l.s[2]==null?999:l.s[2])):null})))"
A,B="[29.2955,-94.7930]","[29.2780,-94.8000]"
def ready(pg): pg.wait_for_function("window.ready===true",timeout=120000)
def toggle(pg,on):
    pg.evaluate("setMenu(true)");pg.wait_for_timeout(500)
    if pg.evaluate("$('vehCart').checked")!=on: pg.click("label.vrow")
    pg.wait_for_function(f"window.ready===true&&MODE==='{'golf_cart' if on else 'lsv'}'&&REG",timeout=120000);pg.wait_for_timeout(1200);pg.evaluate("setSnap('half'),0");pg.wait_for_timeout(600)
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(viewport={"width":430,"height":860},device_scale_factor=2);pg=ctx.new_page()
    pg.goto(URL+GAL);ready(pg)
    ck("default is Off (street-legal LSV, 35 mph)",pg.evaluate("MODE")=="lsv" and pg.evaluate("$('vehCart').checked")==False and pg.evaluate("RULE.max_posted")==35,pg.evaluate("[MODE,RULE.max_posted]"))
    ck("first visit stores the default and the mode version",pg.evaluate("[localStorage.getItem('gcm-veh'),localStorage.getItem('gcm-veh-v')]")==["lsv",pg.evaluate("GCMRule.MODE_VERSION")])
    ck("Texas: Off sublabel says golf carts and LSVs share 35; hint says leave it off",pg.inner_text("#vehTitle")=="Golf cart mode (25 mph roads only)" and pg.inner_text("#vehSub")=="Golf carts and LSVs: roads posted 35 mph or less" and "Leave this off" in pg.inner_text("#vehHint"),pg.inner_text("#vehTitle")+" | "+pg.inner_text("#vehSub")+" | "+pg.inner_text("#vehHint"))
    ck("legend: Unverified Neighborhood Road, 40+ mph / major: avoid, no em dash",pg.inner_text("#lgUnv")=="Unverified Neighborhood Road" and pg.inner_text("#lgNo")=="40+ mph / major: avoid" and "—" not in pg.inner_text("#legend"),pg.inner_text("#legend"))
    ck("legend: Risky stretch hidden while Risky is off",not pg.is_visible("#lgRisk"))
    ck("legend: dotted green swatch for Unverified Neighborhood Road","#4cc38a" in (pg.get_attribute("#lgUnv i","style") or "").lower())
    v35=pg.evaluate(SEG,["Rosenberg Avenue - 25th Street",35,"v"]);v30=pg.evaluate(SEG,["Avenue S",30,"v"]);lo=pg.evaluate(SEG,["Church Street - Avenue F",25,"i","tertiary"])
    ck("found verified 35, verified 30 and a low-confidence tertiary in Galveston",bool(v35 and v30 and lo and lo["unk"]),[v35,v30,lo])
    ck("Off: verified 35 and 30 roads allowed",v35["c"]!=3 and v30["c"]!=3)
    o=pg.evaluate(LINE,lo["p"]);ck("low-confidence road is dotted green, not yellow",o and o["color"]=="#4cc38a" and o["dash"]=="5 4",o and {k:o[k] for k in ("color","dash")})
    ck("popup: Confidence: Low, assumed 25, check signs, no em dash",o and o["txt"].startswith("Church Street - Avenue F") and "Confidence: Low. No posted limit found, so we assume 25 mph. Check signs." in o["txt"] and "—" not in o["txt"] and "Speed unknown" not in o["txt"],o and o["txt"][:300])
    pg.screenshot(path=OUT+"galveston-lowconf-popup.png")
    pg.evaluate("map.closePopup(),map.setView([29.2990,-94.7900],15),0");pg.wait_for_timeout(1800)
    y=pg.evaluate(YELLOW);ck("no yellow road lines drawn",y["all"]>100 and y["n"]==0,y)
    pg.screenshot(path=OUT+"galveston-off.png")
    pg.locator("#legend").screenshot(path=OUT+"legend.png")
    r_off=pg.evaluate(ROUTE%(A,B));ck("Off: route found",bool(r_off["mi"]),r_off)
    sub=pg.inner_text("#sub");ck("route summary has no em dash",r_off["mi"] and "—" not in sub,sub)
    pg.screenshot(path=OUT+"galveston-off-route.png");pg.evaluate("$('reset').click(),0");pg.wait_for_timeout(500)
    toggle(pg,True)
    ck("On: golf cart mode capped at 25 in Texas",pg.evaluate("RULE.max_posted")==25 and pg.evaluate("RULE.veh")=="golf_cart" and pg.inner_text("#vehSub")=="Golf cart: roads posted 25 mph or less",pg.evaluate("[RULE.max_posted,RULE.veh]"))
    v35=pg.evaluate(SEG,["Rosenberg Avenue - 25th Street",35,"v"]);v30=pg.evaluate(SEG,["Avenue S",30,"v"]);lo2=pg.evaluate(SEG,["Church Street - Avenue F",25,"i","tertiary"])
    ck("On: verified 35 and 30 roads not allowed",v35["c"]==3 and v30["c"]==3,[v35,v30])
    ck("On: assumed 25 road still allowed",lo2["c"]!=3)
    o=pg.evaluate(LINE,v35["p"]);ck("On: verified 35 road drawn red",o and o["color"]=="#e5484d",o and o["color"])
    ck("legend in golf cart mode: 26+ mph / major: avoid",pg.inner_text("#lgNo")=="26+ mph / major: avoid",pg.inner_text("#lgNo"))
    pg.evaluate("map.closePopup(),map.setView([29.2990,-94.7900],15),0");pg.wait_for_timeout(1800);pg.screenshot(path=OUT+"galveston-on.png")
    r_on=pg.evaluate(ROUTE%(A,B));ck("On: route never uses a road posted over 25",r_on["mi"] is None or (r_on["max"] is not None and r_on["max"]<=25),r_on)
    pg.screenshot(path=OUT+"galveston-on-route.png");pg.evaluate("$('reset').click(),0");pg.wait_for_timeout(500)
    ck("Off route uses a 30/35 road the On route avoids",r_off["max"] is not None and r_off["max"]>25 and r_off["max"]<=35,[r_off,r_on])
    pg.goto(URL+GAL);ready(pg);ck("On persists after reload",pg.evaluate("MODE")=="golf_cart")
    # Coronado (CA): screenshots in both states
    pg.goto(URL+COR);ready(pg);pg.wait_for_timeout(2000);pg.screenshot(path=OUT+"coronado-on.png")
    ck("Coronado On: 30/35 posted roads closed",pg.evaluate("D.segs.filter(s=>(s[2]===30||s[2]===35)&&s[3]==='v').every(s=>cls(s)===3)"))
    toggle(pg,False);pg.evaluate("map.setView([32.6835,-117.1780],15),0");pg.wait_for_timeout(2000);pg.screenshot(path=OUT+"coronado-off.png")
    ck("Coronado Off: verified 30/35 roads open",pg.evaluate("D.segs.filter(s=>(s[2]===30||s[2]===35)&&s[3]==='v'&&!/^(motorway|trunk|primary)/.test(s[1])).some(s=>cls(s)!==3)"))
    ctx.close()
    # Stored values from before this change (no gcm-veh-v): only an explicit golf_cart stays on.
    for old,want in (("golf_cart","golf_cart"),("lsv","lsv"),("junk","lsv")):
        ctx=b.new_context();pg=ctx.new_page();pg.goto(URL+GAL);ready(pg)
        pg.evaluate(f"localStorage.removeItem('gcm-veh-v');localStorage.setItem('gcm-veh','{old}')");pg.goto(URL+GAL);ready(pg)
        ck(f"legacy stored '{old}' lands on {want}",pg.evaluate("MODE")==want and pg.evaluate("localStorage.getItem('gcm-veh')")==want and pg.evaluate("$('vehCart').checked")==(want=="golf_cart"),pg.evaluate("[MODE,localStorage.getItem('gcm-veh')]"))
        ctx.close()
    b.close()
finish()
