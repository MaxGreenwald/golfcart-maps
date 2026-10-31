"""Browser checks for local-first search (Max t413u) and saved places (Max t414u).
Photon is mocked: a bounded query returns a far result (Seattle) ahead of near San Diego ones; the dropdown must
show the near ones first and no far one above them. Saved Home survives a reload, shows on an empty focused field,
and one tap routes there. Set SHOTS_DIR to save screenshots (keep it outside the repo)."""
import functools, http.server, json, os, socketserver, threading, unittest
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
PUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")
SHOTS = os.environ.get("SHOTS_DIR")

class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
class _S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True

def feat(name, city, lat, lon):
    return {"type": "Feature", "properties": {"name": name, "city": city, "osm_value": "cafe"}, "geometry": {"coordinates": [lon, lat]}}
NEAR_FAR = {"features": [feat("Starbucks", "Seattle", 47.61, -122.33), feat("Starbucks", "San Diego", 32.7495, -117.2134),
                         feat("Starbucks", "San Diego", 32.7975, -117.2510), feat("Starbucks", "New York", 40.75, -73.99)]}
PB = (32.7975, -117.2525)

@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class LocalSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _S(("127.0.0.1", 0), functools.partial(_Quiet, directory=PUB))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start(); cls.b = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls):
        cls.b.close(); cls.pw.stop(); cls.srv.shutdown()

    def page(self):
        c = self.b.new_context(**self.pw.devices["iPhone 13"], geolocation={"latitude": PB[0], "longitude": PB[1]}, permissions=["geolocation"])
        self.addCleanup(c.close)
        pg = c.new_page()
        self.urls = []
        def photon(r):
            self.urls.append(r.request.url); r.fulfill(json=NEAR_FAR if "bbox=" in r.request.url else {"features": []})
        pg.route("**/photon.komoot.io/**", photon)
        pg.route("**/nominatim.openstreetmap.org/**", lambda r: r.fulfill(json=[]))
        pg.route("**/api/e", lambda r: r.fulfill(status=204))
        pg.goto(f"http://127.0.0.1:{self.srv.server_address[1]}/?r=sd")
        pg.wait_for_function("window.ready", timeout=30000)
        pg.evaluate("locate()"); pg.wait_for_function("window.state&&window.state.from&&window.state.from.me", timeout=10000)
        return pg

    def test_near_results_first(self):
        pg = self.page()
        pg.click("#q"); pg.keyboard.type("Starbucks"); pg.wait_for_timeout(1200)
        rows = pg.eval_on_selector_all("#sugg div", "ds=>ds.map(d=>d.textContent)")
        self.assertTrue(rows, "no suggestions")
        self.assertTrue(any("San Diego" in r for r in rows), rows)
        self.assertFalse(any("Seattle" in r or "New York" in r for r in rows), rows)  # near matches exist: far hidden
        self.assertTrue(self.urls and "lat=32.79" in self.urls[0] and "bbox=" in self.urls[0], self.urls)  # biased to me
        mi = [float(r.split(" · ")[-1].split(" ")[0]) for r in rows if r.endswith(" mi") and "Starbucks" in r]
        self.assertEqual(mi, sorted(mi), rows)
        if SHOTS: pg.screenshot(path=os.path.join(SHOTS, "search-starbucks-pb.png"))

    def test_saved_home_and_beach(self):
        pg = self.page()
        pg.click("#q"); pg.wait_for_timeout(200)
        self.assertIn("Set Home", pg.inner_text("#sugg"))
        pg.click("#sugg div:has-text('Set Home')")
        pg.keyboard.type("Starbucks"); pg.wait_for_timeout(1200)
        pg.click("#sugg div:has-text('Starbucks') >> nth=0")
        saved = json.loads(pg.evaluate("localStorage.getItem('gcm-places')"))
        self.assertIn("home", saved)
        pg.evaluate("localStorage.setItem('gcm-places', JSON.stringify(Object.assign(JSON.parse(localStorage.getItem('gcm-places')),{beach:{name:'Tourmaline Surf Park',lat:32.8052,lon:-117.2620}})))")
        pg.goto(f"http://127.0.0.1:{self.srv.server_address[1]}/?r=sd"); pg.wait_for_function("window.ready", timeout=30000)
        self.assertTrue(pg.is_visible(".chip.sp[data-slot=home]")); self.assertTrue(pg.is_visible(".chip.sp[data-slot=beach]"))
        pg.click("#q"); pg.wait_for_timeout(200)
        txt = pg.inner_text("#sugg")
        self.assertIn("Home", txt); self.assertIn("Favorite beach", txt)
        if SHOTS: pg.screenshot(path=os.path.join(SHOTS, "saved-places-dropdown.png"))
        pg.click("#sugg .saved:has-text('Favorite beach')")
        pg.wait_for_function("window.state&&window.state.to", timeout=5000)
        self.assertIn("Favorite beach", pg.input_value("#q"))
        if SHOTS: pg.wait_for_timeout(1500); pg.screenshot(path=os.path.join(SHOTS, "saved-beach-route.png"))

    def test_start_field_gets_saved_place(self):
        """Max t422u: focused Choose start, picked Home, it landed in the destination."""
        pg = self.page()
        pg.evaluate("localStorage.setItem('gcm-places',JSON.stringify({home:{name:'Crystal Pier',lat:32.7963,lon:-117.2571},beach:{name:'Tourmaline Surf Park',lat:32.8052,lon:-117.2620}}))")
        pg.goto(f"http://127.0.0.1:{self.srv.server_address[1]}/?r=sd"); pg.wait_for_function("window.ready", timeout=30000)
        pg.evaluate("from=null;to=null;sync()")
        pg.fill("#qf", ""); pg.click("#qf"); pg.wait_for_timeout(200)
        pg.click("#sugg .saved:has-text('Home')"); pg.wait_for_timeout(300)
        self.assertIn("Home", pg.input_value("#qf"))
        self.assertEqual(pg.input_value("#q"), "")
        self.assertFalse(pg.evaluate("!!(window.state&&window.state.to)"))
        # chip tapped while Start is focused also fills Start
        pg.fill("#qf", ""); pg.click("#qf"); pg.click(".chip.sp[data-slot=beach]"); pg.wait_for_timeout(300)
        self.assertIn("Favorite beach", pg.input_value("#qf")); self.assertEqual(pg.input_value("#q"), "")
        # chips stay on one row
        tops = pg.eval_on_selector_all("#chips>*", "cs=>[...new Set(cs.filter(c=>c.offsetParent).map(c=>c.offsetTop))]")
        self.assertEqual(len(tops), 1, tops)
        if SHOTS: pg.screenshot(path=os.path.join(SHOTS, "start-gets-home.png"))

if __name__ == "__main__":
    unittest.main()
