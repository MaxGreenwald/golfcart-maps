"""South Carolina golf carts cite S.C. Code 56-2-90. Texas cites chapter 551 as published.

Road colors stay on the same posted-speed caps. The half-mile South Carolina event
window and the Texas 5-mile golf-course trip are described in the citation, not drawn
as extra legal roads.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
        return json.load(handle)


class StatuteCites(unittest.TestCase):
    def test_south_carolina_golf_cart_section_and_caps(self):
        rule = load("public/data/rules.json")["SC"]["golf_cart"]
        self.assertIn("S.C. Code 56-2-90", rule["cite"])
        self.assertNotIn("56-2-105", rule["cite"])
        self.assertEqual(rule["url"], "https://www.scstatehouse.gov/code/t56c002.php")
        self.assertEqual(rule["max_posted"], 35)
        self.assertEqual(rule["radius_mi"], 4)
        self.assertTrue(rule["daylight_only"])
        self.assertTrue(rule["cross"])
        self.assertNotIn("\u2014", rule["cite"])

    def test_south_carolina_lsv_section_is_the_35_mph_rule(self):
        rule = load("public/data/rules.json")["SC"]["lsv"]
        self.assertIn("56-2-100", rule["cite"])
        self.assertNotIn("56-5-820", rule["cite"])
        self.assertEqual(rule["max_posted"], 35)
        self.assertTrue(rule["cross"])

    def test_texas_sections_and_caps(self):
        tx = load("public/data/rules.json")["TX"]
        lsv, cart = tx["lsv"], tx["golf_cart"]
        self.assertIn("551.303", lsv["cite"])
        self.assertIn("45 mph", lsv["cite"])
        self.assertNotIn("551.304", lsv["cite"])
        self.assertEqual(lsv["max_posted"], 35)
        self.assertTrue(lsv["cross"])
        self.assertIn("5 miles", cart["cite"])
        self.assertNotIn("2 mi", cart["cite"])
        self.assertIn("551.403", cart["cite"])
        self.assertIn("551.404", cart["cite"])
        self.assertEqual(cart["max_posted"], 35)
        self.assertTrue(cart["daylight_only"])
        self.assertTrue(cart["cross"])
        self.assertNotIn("radius_mi", cart)
        self.assertTrue(lsv["url"].startswith("https://statutes.capitol.texas.gov/"))
        self.assertTrue(cart["url"].startswith("https://statutes.capitol.texas.gov/"))
        self.assertNotIn("\u2014", lsv["cite"])
        self.assertNotIn("\u2014", cart["cite"])

    def test_repealed_section_is_gone_from_published_copy(self):
        needles = []
        for rel in ("public/llms.txt", "public/data/rules.json", "public/data/hhi/index.json"):
            text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            if "56-2-105" in text:
                needles.append(rel)
        town_root = os.path.join(ROOT, "content", "towns")
        for dirpath, _, names in os.walk(town_root):
            for name in names:
                if not name.endswith(".json"):
                    continue
                path = os.path.join(dirpath, name)
                if "56-2-105" in open(path, encoding="utf-8").read() or "551.304" in open(path, encoding="utf-8").read():
                    needles.append(os.path.relpath(path, ROOT))
        self.assertEqual(needles, [])

    def test_port_aransas_summary_cites_551_303(self):
        page = load("content/towns/portaransas/port-aransas.json")
        self.assertIn("551.303", page["lsv"]["notes"])
        self.assertIn("45 mph or less", page["lsv"]["roads"])
        self.assertIn("35 mph or less", page["lsv"]["roads"])
        self.assertEqual(page["lsv"]["speed_line"], "45 mph")
        cites = [row["citation"] for row in page["rules"]]
        self.assertIn("Tex. Transp. Code 551.303", cites)

    def test_hilton_head_ban_label_uses_current_section(self):
        index = load("public/data/hhi/index.json")
        labels = [row[1] for row in index["sources"] if "Cross Island" in row[1]]
        self.assertTrue(labels)
        for label in labels:
            self.assertIn("56-2-90", label)
            self.assertNotIn("56-2-105", label)


if __name__ == "__main__":
    unittest.main()
