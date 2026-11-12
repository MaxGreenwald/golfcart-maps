"""HubSpot embed wiring: public pages include public/hubspot.js once, partner admin does not.

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
COOKIE_POLICY = "https://legal.hubspot.com/cookie-policy"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def count_tags(html):
    return len(TAG.findall(html))


def public_page(rel):
    rel = rel.replace("\\", "/")
    return not (rel == "partner" or rel.startswith("partner/"))


class HubSpotPages(unittest.TestCase):
    def test_loader_source_is_the_public_portal(self):
        src = read(os.path.join(PUB, "hubspot.js"))
        self.assertEqual(src.count(LOADER), 1)
        self.assertNotIn(OLD, src)
        self.assertIsNone(re.search(r"(^|[^:])//js\.hs-scripts\.com", src))
        self.assertNotIn("hs-scripts.com/" + OLD, src)
        self.assertNotIn("Allow HubSpot", src)
        self.assertNotIn("gcm-hs", src)
        sw = read(os.path.join(PUB, "sw.js"))
        self.assertNotIn("hubspot.js", sw)

    def test_static_pages_include_the_loader_except_partner_admin(self):
        for name in ("index.html", "p.html", "404.html", "privacy.html"):
            html = read(os.path.join(PUB, name))
            with self.subTest(name=name):
                self.assertEqual(count_tags(html), 1, name)
                self.assertNotRegex(html, r"<script[^>]+js\.hs-scripts\.com")
                self.assertNotIn(OLD, html)
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
        self.assertEqual(count_tags(sample), 1)
        self.assertNotIn(OLD, home)
        self.assertNotIn("js.hs-scripts.com", home)
        self.assertEqual(home.count("</body>"), 1)
        self.assertNotIn("Allow HubSpot", home)

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
                        self.assertNotRegex(html, r"<script[^>]+js\.hs-scripts\.com")
                        want = 1 if public_page(rel) else 0
                        self.assertEqual(count_tags(html), want, rel)
            self.assertGreater(seen, 10)
            built = read(os.path.join(tmp, "hubspot.js"))
            self.assertEqual(built.count(LOADER), 1)
            self.assertEqual(count_tags(read(os.path.join(tmp, "map.html"))), 1)
            self.assertEqual(count_tags(read(os.path.join(tmp, "index.html"))), 1)
            self.assertEqual(count_tags(read(os.path.join(tmp, "partner", "index.html"))), 0)

    def test_native_map_includes_the_loader_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            B.build(out=tmp, native=True)
            html = read(os.path.join(tmp, "index.html"))
            self.assertEqual(count_tags(html), 1)
            self.assertNotIn("js.hs-scripts.com", html)
            src = read(os.path.join(tmp, "hubspot.js"))
            self.assertIn("isNativePlatform", src)
            self.assertIn("capacitor:", src)

    def test_privacy_policy_matches_first_view_loading(self):
        html = read(os.path.join(PUB, "privacy.html"))
        self.assertIn("Effective November 12, 2026", html)
        self.assertIn("<h2>Cookies and tracking</h2>", html)
        self.assertIn("Golf Cart Maps uses HubSpot cookies on golfcartmap.com for analytics and chat.", html)
        self.assertIn("To opt out, block or delete cookies in your browser settings.", html)
        self.assertIn('href="%s"' % COOKIE_POLICY, html)
        self.assertIn(">HubSpot cookie policy</a>", html)
        self.assertIn("This site does not show a cookie or consent banner.", html)
        self.assertIn("That choice does not stop HubSpot cookies.", html)
        self.assertIn("Collect data from website forms", html)
        self.assertIn('the switch "Collect data from website forms" is off', html)
        self.assertNotIn("has not confirmed that switch is off", html)
        self.assertIn("What these events never include", html)
        self.assertNotIn("Allow HubSpot", html)
        self.assertNotIn("Don't allow", html)
        self.assertNotIn("Turn it off", html)
        self.assertNotIn("gcm-hs", html)
        self.assertNotIn("not loaded until", html)
        self.assertNotIn("\u2014", html)
        self.assertNotIn("\u2013", html)
        self.assertNotIn(OLD, html)
        self.assertNotIn("we never sell your data", html)
        self.assertNotRegex(
            html,
            r"(?i)forms are disabled|form collection is off|will not collect form|we guarantee|GDPR compliant|CCPA compliant|we never use cookies|no cookies",
        )


if __name__ == "__main__":
    unittest.main()
