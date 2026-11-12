"""First view of a public golfcartmap.com page requests HubSpot with no site banner.

The browser job serves dist/ on 127.0.0.1. Chromium maps golfcartmap.com to
that address so location.hostname is the production host. The portal script
is aborted so this run does not finish a HubSpot page view.

Usage: URL=http://127.0.0.1:8765/ python scripts/test_hubspot_first_view.py
"""
import os
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from _check import ck, fail, finish

LOADER = "https://js.hs-scripts.com/52245531.js"
PORT = urlsplit(os.environ.get("URL", "http://127.0.0.1:8765/")).port or 8765
ORIGIN = "http://golfcartmap.com:%d" % PORT
REAL = "try{Object.defineProperty(navigator,'webdriver',{configurable:true,get:()=>false})}catch(e){}"
THIRD = (
    "hs-scripts.com",
    "hs-analytics.net",
    "hs-banner.com",
    "hscollectedforms.net",
    "hsforms.net",
    "usemessages.com",
    "hsappstatic.net",
    "hubspot.com",
    "hubspotusercontent",
)


def third_party(url):
    host = (urlsplit(url).hostname or "").lower()
    return any(part in host for part in THIRD)


def launch_args():
    args = ["--host-resolver-rules=MAP golfcartmap.com 127.0.0.1"]
    if os.environ.get("CHROME"):
        args = ["--no-sandbox", "--disable-dev-shm-usage"] + args
    return args


def arm(page):
    hits = []

    def on_request(request):
        hits.append(request.url)

    def route(route):
        if third_party(route.request.url):
            route.abort()
        else:
            route.continue_()

    page.on("request", on_request)
    page.route("**/*", route)
    page.on("pageerror", lambda err: fail("js " + str(err)))
    return hits


def asked(hits, path):
    return any(urlsplit(url).path == path and (urlsplit(url).hostname or "") == "golfcartmap.com" for url in hits)


def portal(hits):
    return any(url.split("?")[0] == LOADER for url in hits)


def no_prompt(page):
    html = page.content()
    return (
        "Allow HubSpot" not in html
        and "Don't allow" not in html
        and "Turn it off" not in html
        and 'id="gcm-hs"' not in html
    )


def open_public(context, path):
    page = context.new_page()
    hits = arm(page)
    page.goto(ORIGIN + path, wait_until="domcontentloaded")
    page.wait_for_function("document.getElementById('hs-script-loader') !== null", timeout=8000)
    return page, hits


with sync_playwright() as p:
    launch = {"args": launch_args()}
    if os.environ.get("CHROME"):
        launch["executable_path"] = os.environ["CHROME"]
    browser = p.chromium.launch(**launch)
    context = browser.new_context(viewport={"width": 1200, "height": 900})
    context.add_init_script(REAL)

    home, home_hits = open_public(context, "/")
    first = [url for url in home_hits if url.split("?")[0].endswith("/hubspot.js") or url.split("?")[0] == LOADER]
    print("FIRST_VIEW " + " ".join(first))
    ck("home requests /hubspot.js", asked(home_hits, "/hubspot.js"), first)
    ck("home requests the portal script", portal(home_hits), first)
    ck("home has no site consent prompt", no_prompt(home))
    ck("home loader src", home.evaluate("document.getElementById('hs-script-loader').src") == LOADER)

    privacy, privacy_hits = open_public(context, "/privacy")
    ck("privacy requests /hubspot.js", asked(privacy_hits, "/hubspot.js"))
    ck("privacy requests the portal script", portal(privacy_hits))
    ck("privacy has no site consent prompt", no_prompt(privacy))
    ck("cookies heading", privacy.locator("h2", has_text="Cookies and tracking").count() == 1)
    ck("opt out copy", "block or delete cookies" in privacy.content())
    ck("cookie policy link", privacy.locator('a[href="https://legal.hubspot.com/cookie-policy"]').count() == 1)

    town, town_hits = open_public(context, "/sandiego")
    ck("town requests /hubspot.js", asked(town_hits, "/hubspot.js"))
    ck("town requests the portal script", portal(town_hits))
    ck("town has no site consent prompt", no_prompt(town))

    map_page, map_hits = open_public(context, "/map")
    try:
        map_page.wait_for_function("window.ready===true", timeout=120000)
        ck("map still boots", True)
    except Exception as err:
        fail("map still boots", str(err))
    ck("map requests /hubspot.js", asked(map_hits, "/hubspot.js"))
    ck("map requests the portal script", portal(map_hits))
    ck("map has no site consent prompt", no_prompt(map_page))

    partner = context.new_page()
    partner_hits = arm(partner)
    partner.goto(ORIGIN + "/partner/", wait_until="domcontentloaded")
    partner.wait_for_timeout(500)
    ck("partner does not request /hubspot.js", not asked(partner_hits, "/hubspot.js"))
    ck("partner does not request the portal script", not portal(partner_hits))
    ck("partner has no site consent prompt", no_prompt(partner))

    blocked = browser.new_context(viewport={"width": 390, "height": 800})
    bot = blocked.new_page()
    bot_hits = arm(bot)
    bot.goto(ORIGIN + "/", wait_until="domcontentloaded")
    bot.wait_for_timeout(500)
    ck("webdriver still requests /hubspot.js", asked(bot_hits, "/hubspot.js"))
    ck("webdriver does not request the portal script", not portal(bot_hits))
    ck("webdriver has no loader element", bot.evaluate("document.getElementById('hs-script-loader')") is None)
    ck("webdriver has no site consent prompt", no_prompt(bot))

    quiet = browser.new_context(viewport={"width": 390, "height": 800})
    quiet.add_init_script(REAL + ";window.NO_TRACK=1")
    off = quiet.new_page()
    off_hits = arm(off)
    off.goto(ORIGIN + "/", wait_until="domcontentloaded")
    off.wait_for_timeout(500)
    ck("NO_TRACK still requests /hubspot.js", asked(off_hits, "/hubspot.js"))
    ck("NO_TRACK does not request the portal script", not portal(off_hits))
    ck("NO_TRACK has no site consent prompt", no_prompt(off))

    browser.close()

finish()
