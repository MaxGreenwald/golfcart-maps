"""Max (Oct 29 2026): partner portal maps can't be cached; they must have the latest map.

Source checks (always): /data/* is revalidated every request, the service worker sends /p/ and /partner
requests with cache 'no-store' and marks an offline copy, p.js fetches data with no-store and re-checks on focus.
Browser check (needs playwright and a built dist/, as in the web-ci browser job): a renter page ignores a stale
copy in the SW cache while online, and offline it shows "Offline, map may be outdated" instead of silently stale roads.
"""
import functools
import http.server
import os
import re
import socketserver
import threading
import unittest
from urllib.parse import urlsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
DIST = os.path.join(ROOT, "dist")


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


class LatestMapSource(unittest.TestCase):
    def test_data_headers_revalidate_every_time(self):
        h = read(PUB, "_headers")
        block = re.search(r"^/data/\*\n((?:[ \t]+.*\n?)+)", h, re.M)
        self.assertTrue(block, "/data/* block missing")
        cc = re.search(r"Cache-Control:\s*(.*)", block.group(1)).group(1)
        self.assertRegex(cc, r"max-age=0\b")
        self.assertIn("must-revalidate", cc)
        self.assertNotIn("stale-while-revalidate", cc)

    def test_sw_partner_requests_skip_cache_and_mark_offline(self):
        sw = read(PUB, "sw.js")
        self.assertIn(r"/^\/(p|partner)(\/|$)/", sw)
        self.assertIn("cache:'no-store'", sw)
        self.assertIn("X-GCM-Offline", sw)

    def test_renter_page_fetches_fresh_and_rechecks(self):
        p = read(PUB, "p.js")
        self.assertIn("cache: 'no-store'", p)
        self.assertIn("Offline, map may be outdated.", p)
        self.assertIn("visibilitychange", p)
        self.assertIn("openRegion(region, rules, 'golf_cart', freshFetch)", p)
        self.assertNotRegex(p, r"(?<!fresh)fetch\('/data/", "every /data/ fetch in p.js goes through freshFetch")
        self.assertIn("fetch('/data/regions.json', { cache: 'no-store' })", read(PUB, "partner", "admin.js"))


class _H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlsplit(self.path)
        p = u.path
        if p == "/map" or p.startswith("/map/"):
            p = "/map.html"
        elif p == "/p" or p.startswith("/p/"):
            p = "/p.html"
        self.path = p + ("?" + u.query if u.query else "")
        return super().do_GET()


class _S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


SHOP = {"id": "s1", "slug": "fresh", "name": "Fresh Carts", "region_id": "sd", "blurb": "", "logo_url": "", "color": ""}
UNLOCK = {"shop": SHOP, "code": "C1", "experiences": [{"id": "e1", "title": "Loop", "description": "",
          "stops": [{"label": "A", "lat": 32.7965, "lon": -117.2525}, {"label": "B", "lat": 32.8000, "lon": -117.2480}]}],
          "affiliates": []}


def _stamped():
    f = os.path.join(DIST, "sw.js")
    return os.path.isfile(f) and re.search(r"const C='gcm-[0-9a-f]{12}'", read(f)) is not None


@unittest.skipIf(sync_playwright is None or not _stamped(),
                 "needs playwright and a stamped dist/ (python scripts/build_web.py)")
class LatestMapBrowser(unittest.TestCase):
    def test_online_fresh_offline_notice(self):
        srv = _S(("127.0.0.1", 0), functools.partial(_H, directory=DIST))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % srv.server_address[1]
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            c = b.new_context()
            c.route("**/api/partner/**", lambda r: r.fulfill(json=UNLOCK if "unlock" in r.request.url else {"shop": SHOP}))
            pg = c.new_page()
            # p.html doesn't register the SW; a renter who opened /map before is controlled by its scope '/' SW.
            pg.goto(base + "/map")
            pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller !== null", timeout=30000)
            pg.wait_for_timeout(1500)
            pg.goto(base + "/p/fresh/go?code=C1")
            pg.wait_for_function("navigator.serviceWorker.controller !== null && !!window.GCMPartnerFresh", timeout=30000)
            # Plant a stale index in the SW cache, as a phone with yesterday's data would have.
            pg.evaluate("""async () => { const n = (await caches.keys())[0];
              const c = await caches.open(n); await c.put(location.origin + '/data/sd/index.json',
              new Response(JSON.stringify({meta: {generated: 'STALE'}}), {headers: {'Content-Type': 'application/json'}})); }""")
            got = pg.evaluate("fetch('/data/sd/index.json', {cache: 'no-store'}).then(async r => [(await r.json()).meta.generated, r.headers.get('X-GCM-Offline')])")
            self.assertNotEqual(got[0], "STALE", "online renter page must get live data, not the SW copy")
            self.assertIsNone(got[1])
            pg.evaluate("window.GCMPartnerFresh.recheckRoads()")
            self.assertFalse(pg.evaluate("!!document.getElementById('mapStale') && !document.getElementById('mapStale').hidden"))
            c.set_offline(True)
            pg.evaluate("window.GCMPartnerFresh.recheckRoads()")
            pg.wait_for_function("document.getElementById('mapStale') && !document.getElementById('mapStale').hidden", timeout=5000)
            self.assertIn("Offline, map may be outdated", pg.inner_text("#mapStale"))
            pg.goto(base + "/p/fresh/go?code=C1")
            self.assertIn("You are offline", pg.content(), "offline renter navigation gets the offline page, not the /map shell")
            c.set_offline(False)
            b.close()
        srv.shutdown()


if __name__ == "__main__":
    unittest.main()
