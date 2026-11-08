"""Town and city counts on generated pages match public/data/regions.json.

Homepage, /for-rental-shops, /for-manufacturers, the golf cart and LSV hubs,
llms.txt, and the hub ItemList all use that count. The count is produced by
the page generators, not typed in by hand.
"""
import os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import gen_llms
import seo_common as C
import seo_hubs as H
import seo_landing as L
import seo_partner as P

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


class TownCount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = len(C.regions())
        cls.home = L.render()
        cls.maps = H.maps_page()
        cls.lsv = H.lsv_page()
        cls.shops = P.shops_page()
        cls.mfg = P.manufacturers_page()
        cls.llms = gen_llms.render()
        cls.committed = open(os.path.join(ROOT, "public", "llms.txt"), encoding="utf-8").read()

    def test_at_least_100_regions(self):
        self.assertGreaterEqual(self.n, 100)

    def test_homepage_count(self):
        self.assertIn(f"golf cart map for {self.n} towns", self.home)
        self.assertIn(f"for {self.n} beach and golf towns", self.home)
        self.assertIn(f"{self.n} beach and golf towns in", self.home)
        self.assertRegex(self.home, rf"Search any of {self.n} beach and golf towns")

    def test_hubs_and_schema(self):
        self.assertIn(f"Golf cart maps for {self.n} towns", self.maps)
        self.assertIn(f"for {self.n} beach and golf towns", self.maps)
        items = re.search(r'"numberOfItems":\s*(\d+)', self.maps)
        self.assertIsNotNone(items)
        self.assertEqual(int(items.group(1)), self.n)
        self.assertIn(f"for {self.n} beach and golf towns", self.lsv)
        self.assertIn(f"for {self.n} beach and golf towns", re.sub(r"<[^>]+>", " ", self.lsv))

    def test_partner_pages(self):
        self.assertIn(f"<b>{self.n}</b><span>regions live</span>", self.shops)
        self.assertIn(f"{self.n} beach and golf towns", self.mfg)
        self.assertIn(f"{self.n} regions live", self.mfg)

    def test_llms_matches_regions_and_the_committed_file(self):
        phrase = f"in {self.n} beach and golf towns across the U.S."
        self.assertIn(phrase, self.llms)
        self.assertEqual(self.committed, self.llms)
        self.assertTrue(self.committed.strip().endswith("Free to use.") or "free to use" in self.committed.lower())
        # The standing og line is a different sentence and must keep its ending.
        self.assertIn("free to use", self.llms.lower())


if __name__ == "__main__":
    unittest.main()
