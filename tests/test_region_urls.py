"""Every region has a city URL, and _redirects / sitemap.xml / app.js SLUG all match regions.json."""
import os, subprocess, sys, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import region_urls as U


class RegionUrls(unittest.TestCase):
    def test_derived_files_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "region_urls.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_region_has_a_unique_slug(self):
        rs = U.regions()   # raises on a missing/duplicate slug
        self.assertEqual(len({r["slug"] for r in rs}), len(rs))

    def test_every_picker_region_rewrites_to_the_app(self):
        red = open(os.path.join(ROOT, "public", "_redirects")).read().split("\n")
        for r in U.regions():
            with self.subTest(region=r["id"]):
                self.assertIn(f"/{r['slug']} / 200", red)


if __name__ == "__main__":
    unittest.main()
