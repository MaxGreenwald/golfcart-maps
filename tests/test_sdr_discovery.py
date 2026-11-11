"""Public discovery files do not name the SDR chat hosts.

golfcartmap.com itself stays allowed for crawlers. This does not edit the
standalone SDR Worker.
"""
import os
import re
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NEEDLES = (
    "sdr-chat.golfcartmap.com",
    "gcm-sdr-chat.maxgreenwald-assistant.workers.dev",
)
SCAN_EXT = {".html", ".xml", ".txt", ".js", ".json"}
SKIP_DIR = {"data", "node_modules", ".git"}


def read(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def public_files():
    found = []
    base = os.path.join(ROOT, "public")
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in SCAN_EXT:
                found.append(os.path.join(dirpath, name))
    return found


def generator_files():
    scripts = os.path.join(ROOT, "scripts")
    found = []
    for name in os.listdir(scripts):
        if name.startswith("seo_") or name == "gen_llms.py":
            found.append(os.path.join(scripts, name))
    return found


class SdrDiscovery(unittest.TestCase):
    def test_public_pages_do_not_name_sdr_hosts(self):
        hits = []
        for path in public_files() + generator_files():
            text = read(path)
            for needle in NEEDLES:
                if needle in text:
                    hits.append(os.path.relpath(path, ROOT) + ": " + needle)
        self.assertEqual(hits, [])

    def test_main_site_stays_crawlable(self):
        robots = read(os.path.join(ROOT, "public", "robots.txt"))
        self.assertIn("Allow: /", robots)
        self.assertNotRegex(robots, r"(?m)^Disallow: /\s*$")
        self.assertIn("Sitemap: https://golfcartmap.com/sitemap.xml", robots)
        for needle in NEEDLES:
            self.assertNotIn(needle, robots)


if __name__ == "__main__":
    unittest.main()
