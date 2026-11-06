"""LinkedIn company page in the shared SEO footer and Organization sameAs (Max, Nov 6 2026)."""
import json, os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_common as C
import seo_landing
import seo_hubs
import seo_partner


LINK = "https://www.linkedin.com/company/golf-cart-maps"


class LinkedIn(unittest.TestCase):
    def test_org_same_as(self):
        o = C.org()
        self.assertEqual(o["@type"], "Organization")
        self.assertEqual(o.get("sameAs"), [LINK])

    def test_footer_link_style(self):
        # Shared page() footer: Privacy · LinkedIn · Contact, same muted paragraph.
        html = C.page("T", "D ends with Free.", "/x", "<p>hi</p>", [C.org()])
        self.assertIn(f'<a href="{LINK}" target="_blank" rel="noopener">LinkedIn</a>', html)
        self.assertIn('<a href="/privacy">Privacy</a> · ', html)
        self.assertIn(' · Contact: <a href="mailto:', html)
        # Do not touch Free. og text rule elsewhere; this page desc ends with Free. as a smoke check.
        self.assertIn('content="D ends with Free."', html)

    def test_landing_and_partner_pages_include_both(self):
        pages = [
            seo_landing.render(),
            seo_hubs.maps_page(),
            seo_partner.shops_page(),
            seo_partner.manufacturers_page(),
        ]
        for html in pages:
            self.assertIn(LINK, html)
            self.assertIn(">LinkedIn</a>", html)
            ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html).group(1))
            orgs = [x for x in ld if x.get("@type") == "Organization"]
            self.assertEqual(len(orgs), 1, html[:200])
            self.assertEqual(orgs[0].get("sameAs"), [LINK])


if __name__ == "__main__":
    unittest.main()
