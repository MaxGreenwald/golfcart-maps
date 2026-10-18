"""Standing-rule guards listed in AGENTS.md that had no check yet. Run: python3 -m unittest discover -s tests"""
import os, re, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
read = lambda p: open(os.path.join(ROOT, p), encoding="utf-8").read()


class StandingRules(unittest.TestCase):
    def test_not_legal_advice_disclaimer_stays(self):
        # plan.md: never remove the not-legal-advice disclaimers.
        html = read("public/index.html")
        self.assertRegex(html, r'<div id="disc">[^<]*<b>[^<]*not legal advice', "map disclaimer bar (#disc) missing")
        self.assertIn("Posted signs always take precedence over the map.", html)
        self.assertIn("Not legal advice", read("public/llms.txt"))

    def test_og_free_text_untouched(self):
        # Max: don't touch the 'Free.' og text (share previews).
        m = re.search(r'property="og:description" content="([^"]*)"', read("public/index.html"))
        self.assertTrue(m and m.group(1).endswith(" Free."), "og:description must keep its closing 'Free.'")

    def test_production_deploy_guard(self):
        # Production deploys only from master with a clean public/functions/lib tree (and only with Max's OK).
        sh = read("scripts/deploy_web.sh")
        self.assertIn('[ "$cur" = master ]', sh)
        self.assertIn("git status --porcelain -- public functions lib", sh)


if __name__ == "__main__":
    unittest.main()
