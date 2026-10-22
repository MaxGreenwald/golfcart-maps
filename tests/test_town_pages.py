"""Published town pages (content/towns/<region>/*.json -> dist/<region>/<town>.html): JSON-LD valid with FAQPage that
matches the visible FAQ, every page cites an http(s) source and shows 'Rules last checked YYYY-MM-DD', no 'beta'
wording, Open-the-map link goes to /map/<live region slug> with a center inside that region, nearby links resolve,
and every page is in the sitemap. Set URL=https://<preview>/ to also fetch every page and map link over HTTP."""
import glob, json, os, re, shutil, sys, tempfile, unittest, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_towns as T, seo_common as C
FILES = sorted(glob.glob(os.path.join(T.TOWNS, "*", "*.json")))
REGS = {r["slug"]: r for r in C.regions()}
class TownPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = tempfile.mkdtemp(); open(os.path.join(cls.out, "sitemap.xml"), "w").write("<urlset></urlset>")
        cls.made = T.build(cls.out); cls.sm = open(os.path.join(cls.out, "sitemap.xml")).read()
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.out)
    def pages(self):
        for t in self.made: yield t, open(os.path.join(self.out, t["region"], t["slug"] + ".html")).read()
    def test_count(self): self.assertGreaterEqual(len(self.made), 50)
    def test_schema(self):
        for t, h in self.pages():
            ld = json.loads(re.search(r'application/ld\+json">(.*?)</script>', h, re.S).group(1))
            types = {x["@type"] for x in ld}; self.assertTrue({"WebPage", "BreadcrumbList", "FAQPage"} <= types, t["slug"])
            for x in ld: self.assertEqual(x["@context"], "https://schema.org")
            fq = [x for x in ld if x["@type"] == "FAQPage"][0]["mainEntity"]
            self.assertEqual(len(fq), len(t["faq"])); self.assertGreaterEqual(len(fq), 2)
            for q in fq:
                self.assertEqual(q["@type"], "Question"); self.assertEqual(q["acceptedAnswer"]["@type"], "Answer")
                self.assertIn(C.e(q["name"]), h); self.assertIn(C.e(q["acceptedAnswer"]["text"]), h)
    def test_source_and_checked_date(self):
        for t, h in self.pages():
            self.assertTrue(t["rules"] and all(re.match(r"^https?://", r["source_url"]) for r in t["rules"]), t["slug"])
            self.assertRegex(h, r'<td><a href="https?://[^"]+" rel=nofollow>')
            self.assertRegex(h, r"Rules last checked \d{4}-\d{2}-\d{2}")
    def test_no_beta_wording(self):
        for t, h in self.pages():
            self.assertNotRegex(re.sub(r"<[^>]+>", " ", h), r"(?i)\bbeta\b|verified", t["slug"])
            self.assertIn("is free to use", h); self.assertIn("Golf Cart Maps", h)
    def test_map_and_nearby_links(self):
        for t, h in self.pages():
            r = REGS[t["region"]]; lat, lon = t["map_center"]; b = r["bbox"]
            self.assertTrue(b[0] <= lat <= b[2] and b[1] <= lon <= b[3], f"{t['slug']} center outside {r['id']}")
            self.assertIn(f'href="/map/{t["region"]}?lat=', h)
            for n in t["nearby"]: self.assertTrue(os.path.exists(os.path.join(self.out, t["region"], n + ".html")), (t["slug"], n))
            self.assertIn(f"<loc>{C.SITE}/{t['region']}/{t['slug']}</loc>", self.sm)
    def test_live_http(self):
        base = os.environ.get("URL")
        if not base: self.skipTest("set URL to fetch pages over HTTP")
        base = base.rstrip("/")
        for t, _ in self.pages():
            for p in (f"/{t['region']}/{t['slug']}", f"/map/{t['region']}"):
                with urllib.request.urlopen(urllib.request.Request(base + p, headers={"User-Agent": "gcm-test"})) as r:
                    self.assertEqual(r.status, 200, p); body = r.read().decode()
                    if p.startswith("/map/"): self.assertIn("leaflet", body.lower())
                    else: self.assertIn(t["question_title"].replace("'", "&#x27;"), body)
if __name__ == "__main__": unittest.main()
