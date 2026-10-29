"""robots.txt names the AI crawlers; llms.txt is national, generated, never says beta/verified."""
import os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import gen_llms
PUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")
class T(unittest.TestCase):
    def test_robots(self):
        t = open(os.path.join(PUB, "robots.txt")).read()
        for ua in ["GPTBot","OAI-SearchBot","ChatGPT-User","ClaudeBot","PerplexityBot","Google-Extended","meta-webindexer","Meta-ExternalAgent","Bingbot","Applebot-Extended"]:
            self.assertIn("User-agent: " + ua + "\n", t)
        self.assertIn("Sitemap: https://golfcartmap.com/sitemap.xml", t)
        self.assertNotRegex(t, r"(?m)^Disallow: /\s*$")
    def test_llms_current_and_clean(self):
        t = open(os.path.join(PUB, "llms.txt")).read()
        self.assertEqual(t, gen_llms.render(), "run scripts/gen_llms.py")
        self.assertNotRegex(t, r"(?i)\bbeta\b|verified|android")
        self.assertIn("free to use", t)
        for s in ["sandiego", "villages", "30a", "keywest"]: self.assertIn("https://golfcartmap.com/%s)" % s, t)
if __name__ == "__main__": unittest.main()
