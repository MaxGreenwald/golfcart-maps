"""Regression (iOS build 18, Chloe Belle, Oct 19): typed destination text vanished as soon as suggestions showed.
Cause: every GPS tick (watchPosition, start = Your location) ran sync(), which rewrote #q from state (to=null -> '').
Out of region (Phoenix -> nearest-region fallback Sun City) and SD are both checked."""
import functools, http.server, os, socketserver, threading, unittest
from playwright.sync_api import sync_playwright
PUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")

class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
class _S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True

class SearchKeepsText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _S(("127.0.0.1", 0), functools.partial(_Quiet, directory=PUB))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start(); cls.b = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls):
        cls.b.close(); cls.pw.stop(); cls.srv.shutdown()

    def run_case(self, lat, lng, region, text):
        c = self.b.new_context(**self.pw.devices["iPhone 13"], geolocation={"latitude": lat, "longitude": lng}, permissions=["geolocation"])
        try:
            pg = c.new_page()
            pg.route("**/photon.komoot.io/**", lambda r: r.fulfill(json={"features": []}))
            pg.route("**/nominatim.openstreetmap.org/**", lambda r: r.fulfill(json=[]))
            pg.route("**/api/e", lambda r: r.fulfill(status=204))
            pg.goto(f"http://127.0.0.1:{self.srv.server_address[1]}/?r=x")
            pg.wait_for_function("window.ready", timeout=30000)
            pg.evaluate("locate()"); pg.wait_for_function("window.state&&window.state.from&&window.state.from.me", timeout=10000)
            self.assertEqual(pg.evaluate("REG.id"), region)
            pg.click("#q"); pg.keyboard.type(text); pg.wait_for_timeout(400)
            for i in range(3):  # stationary phone still gets GPS fixes
                c.set_geolocation({"latitude": lat + 1e-6 * (i + 1), "longitude": lng}); pg.wait_for_timeout(400)
            self.assertEqual(pg.input_value("#q"), text)
            return pg
        finally:
            pass

    def test_out_of_region_keeps_text_when_suggestions_arrive(self):
        pg = self.run_case(33.5, -112.07, "suncity", "60")
        self.assertEqual(pg.evaluate("$('sugg').style.display"), "block")  # 'Arapaho Village Units 201-560' showed
        pg.click("#sugg div"); pg.wait_for_timeout(300)                 # picking still fills the box
        self.assertIn("Arapaho", pg.input_value("#q")); pg.context.close()

    def test_sd_keeps_text(self):
        self.run_case(32.79, -117.25, "sd", "737").context.close()

if __name__ == "__main__": unittest.main()
