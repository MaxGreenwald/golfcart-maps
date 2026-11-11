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

    def test_static_pages_include_the_gate_only_on_privacy(self):
        privacy = read(os.path.join(PUB, "privacy.html"))
        self.assertEqual(count_tags(privacy), 1)
        self.assertNotRegex(privacy, r"<script[^>]+js\.hs-scripts\.com")
        for name in ("index.html", "p.html", "404.html"):
            html = read(os.path.join(PUB, name))
            with self.subTest(name=name):
                self.assertEqual(count_tags(html), 0, name)
                self.assertNotIn(OLD, html)

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
        self.assertEqual(count_tags(home), 1)
        self.assertEqual(count_tags(sample), 0)
        self.assertNotIn(OLD, home)
        self.assertNotIn("js.hs-scripts.com", home)
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
                        want = 1 if rel in ("index.html", "privacy.html") else 0
                        self.assertEqual(count_tags(html), want, rel)
            self.assertGreater(seen, 10)
            built = read(os.path.join(tmp, "hubspot.js"))
            self.assertEqual(built.count(LOADER), 1)
            self.assertNotIn("hubspot.js", read(os.path.join(tmp, "map.html")))
            self.assertEqual(count_tags(read(os.path.join(tmp, "index.html"))), 1)

    def test_privacy_policy_matches_the_opt_in(self):
        html = read(os.path.join(PUB, "privacy.html"))
        self.assertIn("Effective November 11, 2026", html)
        self.assertIn("homepage https://golfcartmap.com/", html)
        self.assertIn("not loaded until you click Allow HubSpot", html)
        self.assertIn("Collect data from website forms", html)
        self.assertIn('the switch "Collect data from website forms" is off', html)
        self.assertNotIn("has not confirmed that switch is off", html)
        self.assertIn("What these events never include", html)
        self.assertNotIn(OLD, html)
        self.assertNotIn("we never sell your data", html)
        self.assertNotRegex(
            html,
            r"(?i)forms are disabled|form collection is off|will not collect form|we guarantee|GDPR compliant|CCPA compliant|we never use cookies|no cookies",
        )


if __name__ == "__main__":
    unittest.main()
