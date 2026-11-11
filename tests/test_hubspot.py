"""HubSpot embed wiring: one public/hubspot.js include on public pages, none on partner admin.

The loader itself is tests/hubspot.test.mjs. This checks source HTML, generated
SEO pages, and a web build of dist/.
"""
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import build_web as B
import seo_common as C
import seo_landing as L

ROOT = B.ROOT
PUB = os.path.join(ROOT, "public")
TAG = re.compile(r'<script\s+defer\s+src="(?:/)?hubspot\.js"></script>')
OLD = "247729169"
PORTAL = "52245531"
LOADER = "https://js.hs-scripts.com/" + PORTAL + ".js"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def count_tags(html):
    return len(TAG.findall(html))


class HubSpotPages(unittest.TestCase):
    def test_loader_source_is_the_public_portal(self):
        src = read(os.path.join(PUB, "hubspot.js"))
        self.assertEqual(src.count(LOADER), 1)
        self.assertNotIn(OLD, src)
        self.assertIsNone(re.search(r"(^|[^:])//js\.hs-scripts\.com", src))
        self.assertNotIn("hs-scripts.com/" + OLD, src)
        sw = read(os.path.join(PUB, "sw.js"))
        self.assertNotIn("hubspot.js", sw)

    def test_static_public_pages_include_it_once(self):
        for name in ("index.html", "p.html", "privacy.html", "404.html"):
            html = read(os.path.join(PUB, name))
            with self.subTest(name=name):
                self.assertEqual(count_tags(html), 1, name)
                self.assertNotIn(OLD, html)
                self.assertNotIn("js.hs-scripts.com", html)

    def test_partner_admin_has_no_loader(self):
        html = read(os.path.join(PUB, "partner", "index.html"))
        admin = read(os.path.join(PUB, "partner", "admin.js"))
        self.assertEqual(count_tags(html), 0)
        self.assertNotIn("hubspot", html.lower())
        self.assertNotIn("hubspot", admin.lower())
        self.assertNotIn(OLD, html)

    def test_generated_pages_include_it_once(self):
        home = L.render()
        sample = C.page("Town", "A town page.", "/sample", "<p>Hello</p>", [])
        for label, html in (("landing", home), ("page", sample)):
            with self.subTest(label=label):
                self.assertEqual(count_tags(html), 1, label)
                self.assertNotIn(OLD, html)
                self.assertNotIn("js.hs-scripts.com", html)
        self.assertEqual(home.count("</body>"), 1)

    def test_web_build_keeps_one_tag_on_public_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            B.build(out=tmp, native=False)
            seen = 0
            for dirpath, dirnames, filenames in os.walk(tmp):
                dirnames[:] = [d for d in dirnames if d != "data"]
                for name in filenames:
                    if not name.endswith(".html"):
                        continue
                    rel = os.path.relpath(os.path.join(dirpath, name), tmp)
                    html = read(os.path.join(dirpath, name))
                    seen += 1
                    with self.subTest(rel=rel):
                        self.assertNotIn(OLD, html)
                        if rel.startswith("partner" + os.sep) or rel.startswith("partner/"):
                            self.assertEqual(count_tags(html), 0, rel)
                        else:
                            self.assertEqual(count_tags(html), 1, rel)
            self.assertGreater(seen, 10)
            built = read(os.path.join(tmp, "hubspot.js"))
            self.assertEqual(built.count(LOADER), 1)
            self.assertIn('src="hubspot.js"', read(os.path.join(tmp, "map.html")))
            self.assertIn('src="/hubspot.js"', read(os.path.join(tmp, "index.html")))


if __name__ == "__main__":
    unittest.main()
