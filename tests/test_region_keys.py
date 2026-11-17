"""Unknown or misspelled keys in regions.json must fail CI.

The app reads region.rule (see public/roadrule.js ruleFor). A typo such as
"rules" is ignored, and the town falls back to the state default. That is how
The Villages was silently using Florida's designated-roads rule.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import validate_data as V

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def load_regions():
    with open(os.path.join(ROOT, "public", "data", "regions.json"), encoding="utf-8") as handle:
        return json.load(handle)


class RegionKeys(unittest.TestCase):
    def test_allowed_keys_include_rule_not_rules(self):
        self.assertIn("rule", V.REGION_KEYS)
        self.assertNotIn("rules", V.REGION_KEYS)

    def test_live_regions_have_only_known_keys(self):
        self.assertEqual(V.unknown_region_keys(load_regions()), [])

    def test_rules_typo_is_rejected(self):
        found = V.unknown_region_keys([{"id": "sample", "name": "Sample", "rules": {}}])
        self.assertEqual(found, [("sample", ["rules"])])

    def test_other_unknown_or_misspelled_keys_are_rejected(self):
        found = V.unknown_region_keys([{"id": "sample", "Rule": {}, "ruleset": 1}])
        self.assertEqual(found, [("sample", ["Rule", "ruleset"])])

    def test_known_keys_alone_pass(self):
        region = {key: 1 for key in V.REGION_KEYS}
        region["id"] = "sample"
        self.assertEqual(V.unknown_region_keys([region]), [])

    def test_villages_uses_rule_with_local_golf_cart_cap(self):
        villages = next(r for r in load_regions() if r["id"] == "villages")
        self.assertIn("rule", villages)
        self.assertNotIn("rules", villages)
        cart = villages["rule"]["golf_cart"]
        self.assertEqual(cart["max_posted"], 30)
        self.assertIn("residential", cart["assume"])


if __name__ == "__main__":
    unittest.main()
