"""Private Bintelli coverage page (/coverage/<random>/): unlisted, noindex, data current with research/bintelli_coverage.py."""
import json, os, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "public", "coverage", "8fvdpdeqf4fb")
class T(unittest.TestCase):
    def test_noindex(self):
        h = open(os.path.join(PAGE, "index.html")).read()
        self.assertIn('<meta name="robots" content="noindex,nofollow,noarchive">', h)
        self.assertIn("/coverage/*\n  X-Robots-Tag: noindex", open(os.path.join(ROOT, "public", "_headers")).read())
        self.assertNotIn("<img", h)   # no partner logos
    def test_unlisted(self):
        for f in ("sitemap.xml", "llms.txt", "robots.txt", "index.html", "_redirects"):
            self.assertNotIn("coverage/", open(os.path.join(ROOT, "public", f)).read(), f)
    def test_data_current(self):
        with tempfile.NamedTemporaryFile(suffix=".json") as t:
            subprocess.run([sys.executable, os.path.join(ROOT, "research", "bintelli_coverage.py"), "--page-json", t.name], check=True, capture_output=True)
            self.assertEqual(json.load(open(t.name)), json.load(open(os.path.join(PAGE, "data.json"))), "rerun research/bintelli_coverage.py --page-json")
        d = json.load(open(os.path.join(PAGE, "data.json")))
        self.assertEqual(len(d["regions"]), len(json.load(open(os.path.join(ROOT, "public", "data", "regions.json")))))
        self.assertEqual(d["summary"]["own_store"]["n"], 17)
if __name__ == "__main__": unittest.main()
