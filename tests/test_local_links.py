"""Every row of the Oct 22 backlinks list renders as a followed, descriptive Local resources link on its town or region page."""
import csv, glob, json, os, re, shutil, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import seo_towns as T, seo_pages as P, seo_common as C
DROPPED = {"https://www.cityofmarcoisland.com/police/page/low-speed-vehicles"}  # 404 on Oct 22, 2026
def all_resources():
    for f in glob.glob(os.path.join(T.TOWNS, "*", "*.json")):
        t = json.load(open(f)); yield "/%s/%s" % (t["region"], t["slug"]), t.get("local_resources", [])
    for slug, items in json.load(open(P.RES)).items(): yield "/" + slug, items
class LocalLinks(unittest.TestCase):
    def test_counts_and_shape(self):
        items = [(p, r) for p, L in all_resources() for r in L]
        self.assertEqual(len(items), 49)
        urls = [r["url"] for _, r in items]; self.assertEqual(len(urls), len(set(urls)))
        self.assertFalse(DROPPED & set(urls))
        for p, r in items:
            self.assertTrue(r["url"].startswith("https://"), r)
            self.assertGreaterEqual(len(r["name"].split()), 3, r)  # descriptive anchor, not "click here"
            self.assertNotRegex(" ".join(r.values()), r"(?i)\bbeta\b|click here")
    def test_region_page_renders_followed(self):
        out = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, out); P.build(out)
        h = open(os.path.join(out, "outerbanks.html")).read()
        sec = h.split("<h2>Local resources</h2>", 1)[1].split("</ul>", 1)[0]
        for a in re.findall(r'<a [^>]*>', sec): self.assertNotIn("nofollow", a)
        self.assertIn('href="https://www.outerbanks.org/"', sec); self.assertIn('href="https://www.nagsheadnc.gov/"', sec)
        self.assertNotIn("Local resources", open(os.path.join(out, "sandiego.html")).read())
    def test_town_page_renders_every_link(self):
        out = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, out)
        open(os.path.join(out, "sitemap.xml"), "w").write("<urlset></urlset>"); T.build(out)
        h = open(os.path.join(out, "sandiego", "coronado.html")).read()
        sec = h.split("<h2>Local resources</h2>", 1)[1].split("</ul>", 1)[0]
        self.assertEqual(sec.count("<li>"), 2); self.assertNotIn("nofollow", sec)
if __name__ == "__main__": unittest.main()
