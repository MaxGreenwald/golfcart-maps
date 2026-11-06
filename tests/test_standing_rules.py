"""Standing rules 8 and 9: disclaimers stay, and the og share text stays.

The map bar is #disc. The page keeps "Posted signs always take precedence".
llms.txt keeps the not-legal-advice line. og:description ends with "Free to use."
That share sentence is frozen; do not edit the page copy to satisfy this test.
"""
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# Map share text (public/index.html). Max's "Free." line, now "Free to use."
OG = (
    "Hop in and cruise! See every golf cart &amp; LSV-legal road in San Diego, "
    "Naples, The Villages, 30A, Myrtle Beach and more, dodge the fast no-go roads, "
    "and get a beach-to-tacos route in seconds. Free to use."
)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
        return handle.read()


class StandingRules(unittest.TestCase):
    def test_not_legal_advice_disclaimer_stays(self):
        html = read("public/index.html")
        self.assertRegex(html, r"#disc\s*\{", "map disclaimer bar style (#disc) missing")
        self.assertRegex(
            html,
            r'<div id="disc">[^<]*<b>[^<]*not legal advice',
            "map disclaimer bar (#disc) missing",
        )
        self.assertIn("Posted signs always take precedence over the map.", html)
        llms = read("public/llms.txt")
        self.assertIn("Not legal advice", llms)
        self.assertIn("Not legal advice", read("scripts/gen_llms.py"))

    def test_og_free_text_untouched(self):
        html = read("public/index.html")
        ogs = re.findall(r'property="og:description" content="([^"]*)"', html)
        self.assertTrue(ogs, "og:description missing")
        for content in ogs:
            self.assertTrue(content.endswith("Free to use."), content)
            self.assertEqual(content, OG)
        twitters = re.findall(r'name="twitter:description" content="([^"]*)"', html)
        self.assertTrue(twitters, "twitter:description missing")
        for content in twitters:
            self.assertTrue(content.endswith("Free to use."), content)
            self.assertEqual(content, OG)
        positioning = read("scripts/positioning.py")
        self.assertIn('LANDING_DESC_TAIL = " Free to use."', positioning)


if __name__ == "__main__":
    unittest.main()
