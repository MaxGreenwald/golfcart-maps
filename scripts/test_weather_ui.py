"""Weather banner (iPhone viewport) with a stubbed Open-Meteo response: shows the most serious alert for the route,
dismiss keeps it quiet, next alert kind appears, Settings off switch, clear weather -> no banner, API down -> silent."""
from playwright.sync_api import sync_playwright
import os,sys,json
URL=os.environ.get("URL","http://localhost:8765/");fails=[]
def ck(n,c,x=""):print("PASS" if c else "FAIL",n,"" if c else str(x)[:300]);(None if c else fails.append(n))
A,B=[32.8328,-117.2713],[32.8180,-117.2700]
T=['2026-10-19T13:00','2026-10-19T14:00','2026-10-19T15:00','2026-10-19T16:00']
STORM={"hourly":{"time":T,"precipitation_probability":[0,80,90,0],"precipitation":[0,2,4,0],"weather_code":[0,0,95,0],"wind_speed_10m":[5,5,5,5],"wind_gusts_10m":[8,8,8,8]}}
CLEAR={"hourly":{"time":T,"precipitation_probability":[1,1,1,1],"precipitation":[0,0,0,0],"weather_code":[0,0,0,0],"wind_speed_10m":[3,3,3,3],"wind_gusts_10m":[5,5,5,5]}}
with sync_playwright() as p:
    b=p.chromium.launch();ctx=b.new_context(**p.devices["iPhone 13"]);pg=ctx.new_page()
    pg.on("pageerror",lambda e:fails.append("js error "+str(e)))
    pg.add_init_script("localStorage.setItem('gcm-notrack','1')")
    calls=[];mode={"r":STORM}
    def h(route):
        calls.append(route.request.url)
        if mode["r"] is None:route.abort()
        else:route.fulfill(status=200,content_type="application/json",body=json.dumps(mode["r"]))
    pg.route("https://api.open-meteo.com/**",h)
    pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    ck("no weather call before a route",not calls)
    pg.evaluate(f"testRoute({A},{B})");pg.wait_for_selector("#wx",state="visible",timeout=10000)
    t=pg.inner_text("#wx");ck("lightning banner first","Thunderstorms" in t and "3 PM" in t,t)
    ck("no API key in request","key" not in calls[0] and "latitude=32.83" in calls[0],calls)
    if os.environ.get("SHOT"):pg.screenshot(path="shots/weather.png")
    pg.click("#wx .wxx");ck("dismiss hides",not pg.is_visible("#wx"))
    pg.evaluate(f"testRoute({A},{B})");pg.wait_for_timeout(500);t=pg.inner_text("#wx") if pg.is_visible("#wx") else ""
    ck("dismissed stays quiet, next kind shows","Rain likely" in t and "Thunder" not in t,t)
    ck("cached (one call)",len(calls)==1,calls)
    pg.click("#wx .wxx");pg.evaluate(f"testRoute({A},{B})");pg.wait_for_timeout(500);ck("all dismissed -> nothing",not pg.is_visible("#wx"))
    pg.evaluate("localStorage.removeItem('gcm-wx-dis')");pg.evaluate("setWx(false)");pg.evaluate(f"testRoute({A},{B})");pg.wait_for_timeout(500)
    ck("Settings off -> no banner",not pg.is_visible("#wx") and not pg.is_checked("#setWx"))
    pg.evaluate("setWx(true)");pg.goto(URL);pg.wait_for_function("window.ready===true",timeout=120000)
    ck("setting remembered",pg.is_checked("#setWx"))
    mode["r"]=CLEAR;pg.evaluate(f"testRoute({A},{B})");pg.wait_for_timeout(800);ck("clear weather -> no banner",not pg.is_visible("#wx"))
    mode["r"]=None;pg.evaluate("wxCheck(L.latLng(33.1,-117.3))");pg.wait_for_timeout(800);ck("API down -> silent",not pg.is_visible("#wx"))
    pg.evaluate("resetRoute()");ck("hidden after reset",not pg.is_visible("#wx"))
    b.close()
print("RESULT","ALL PASS" if not fails else "FAIL "+str(fails));sys.exit(1 if fails else 0)
