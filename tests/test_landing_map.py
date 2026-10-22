"""Landing page at /, map at /map, native build keeps the map as index.html, SW shell is /map."""
import json, os, re, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import build_web as B, seo_landing as L, seo_common as C
class Landing(unittest.TestCase):
    def test_web_and_native_builds(self):
        with tempfile.TemporaryDirectory() as t:
            B.build(out=os.path.join(t, "w"), native=False); B.build(out=os.path.join(t, "n"), native=True)
            w, m = open(os.path.join(t, "w", "index.html")).read(), open(os.path.join(t, "w", "map.html")).read()
            n = open(os.path.join(t, "n", "index.html")).read()
            self.assertIn("<h1>Cruise anywhere your cart is legal.", w); self.assertNotIn("leaflet", w.lower())
            self.assertIn('id="map"', m); self.assertIn('<link rel="canonical" href="https://golfcartmap.com/map">', m)
            self.assertIn('id="map"', n); self.assertFalse(os.path.exists(os.path.join(t, "n", "map.html")))
            src = open(os.path.join(C.PUB, "index.html")).read()
            for frozen in re.findall(r'<meta (?:property="og:description"|name="twitter:description")[^>]*>', src):
                self.assertIn(frozen, m); self.assertTrue(frozen.endswith('Free to use.">'))   # og/twitter text: Max Oct 22 'Free to use'
    def test_landing_content(self):
        h = L.render()
        self.assertIn('<link rel="canonical" href="https://golfcartmap.com/">', h)
        self.assertEqual(len(re.findall(r'class="cta" href="/map" target="_blank" rel="noopener"', h)), 2)
        first_p = re.search(r"</h1>\s*<p>(.*?)</p>", h, re.S).group(1); self.assertLessEqual(len(first_p.split()), 60)
        ld = json.loads(re.search(r'application/ld\+json">(.*?)</script>', h, re.S).group(1))
        self.assertEqual({x["@type"] for x in ld}, {"Organization", "WebSite", "SoftwareApplication", "MobileApplication", "FAQPage"})
        self.assertNotIn("offers", [x for x in ld if x["@type"] == "SoftwareApplication"][0])
        for q in [x for x in ld if x["@type"] == "FAQPage"][0]["mainEntity"]: self.assertIn(C.e(q["acceptedAnswer"]["text"]), h)
        self.assertNotRegex(re.sub(r"<[^>]+>", " ", h), r"(?i)\bbeta\b|verified|android")
        for r in C.regions(): self.assertIn(f'href="/{r["slug"]}"', h)
        self.assertIn("window.Capacitor", h)  # native app never shows the landing page
    def test_sw_shell_is_map(self):
        sw = open(os.path.join(C.PUB, "sw.js")).read()
        self.assertIn("const PRE=['map',", sw); self.assertNotIn("put('./'", sw); self.assertIn("caches.match('map')", sw)
        self.assertEqual(B._entry_path("map"), "index.html")
    def test_checkout_and_manifest_point_at_map(self):
        self.assertIn("/map?paid=", open(os.path.join(B.ROOT, "functions", "api", "checkout.js")).read())
        self.assertEqual(json.load(open(os.path.join(C.PUB, "site.webmanifest")))["start_url"], "/map")
    def test_root_function(self):
        js = ("import('%s').then(m=>{const o=[m.target('https://x/?lat=1&lon=2&z=3',''),m.target('https://x/?utm_source=qr',''),"
              "m.target('https://x/','a=1; gcm_skip=1'),m.target('https://x/?paid=cancel',''),m.target('https://x/','gcm_skip=0')];console.log(JSON.stringify(o))})") % os.path.join(B.ROOT, "functions", "index.js")
        o = json.loads(subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, check=True).stdout)
        self.assertEqual(o, [{"location": "/map?lat=1&lon=2&z=3", "reason": "param"}, None, {"location": "/map", "reason": "cookie"},
                             {"location": "/map?paid=cancel", "reason": "param"}, None])
if __name__ == "__main__": unittest.main()
