"""CarPlay JS bridge: status, plan (SD + Villages, both modes), maneuvers, overlay, search."""
from playwright.sync_api import sync_playwright
import os,json
URL=os.environ.get("URL","http://localhost:8767/");fails=[]
def ck(n,c,x=""):print("PASS" if c else "FAIL",n,str(x)[:300]);(None if c else fails.append(n))
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page();pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    st=pg.evaluate("GCMCarPlay.status()");ck("status",st["region"]=="sd" and len(st["regions"])>=3,st)
    r=pg.evaluate("GCMCarPlay.plan({lat:32.8328,lon:-117.2713},{lat:32.7950,lon:-117.2530},'lsv')")
    ck("sd plan",r["ok"] and len(r["line"])>10 and r["maneuvers"][0]["type"]=="depart" and r["maneuvers"][-1]["type"]=="arrive",{k:r[k] for k in r if k not in("line",)} if r["ok"] else r)
    ck("sd turns",any(m["type"] in("left","right") for m in r["maneuvers"]),[m["text"] for m in r["maneuvers"]])
    ms=r["maneuvers"];ck("toMeters chain",all(ms[i]["toMeters"]==ms[i-1]["meters"] for i in range(1,len(ms))),[(m["toMeters"],m["meters"]) for m in ms])
    ck("turn angles + short text",all("turn" in m and m.get("short") for m in ms) and all((m["turn"]>0)==(m["type"].endswith("right")) for m in ms if m["type"] in("left","right")),[(m["type"],m["turn"]) for m in ms])
    ck("no unnamed straights",not any(m["type"]=="straight" and m["road"]=="unnamed road" for m in ms),[m["text"] for m in ms])
    ck("range info",r["range"] and "status" in r["range"],r.get("range"))
    pg.evaluate("GCMCarPlay.setMode('golf_cart')")  # plan() ignores its mode arg; the saved setting decides
    v=pg.evaluate("GCMCarPlay.plan({lat:28.9095,lon:-81.9745},{lat:28.9330,lon:-81.9590},'golf_cart')")
    ck("villages auto-region golf cart plan",v["ok"] and v["region"]=="villages" and v["mode"]=="golf_cart" and v["miles"]<15,{k:v[k] for k in v if k not in("line","maneuvers")})
    o=pg.evaluate("GCMCarPlay.overlay(28.90,-81.99,28.92,-81.96,800)");ck("overlay",len(o["ok"])>20,(len(o["ok"]),len(o["bad"])))
    s=pg.evaluate("GCMCarPlay.search('spanish',28.91,-81.97)");ck("search",len(s)>0,s)
    pg.evaluate("GCMCarPlay.setMode('lsv')")
print("FAILS:",fails);exit(1 if fails else 0)
