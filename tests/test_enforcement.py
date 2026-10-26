"""Every live region must record its local enforcement source check (scripts/check_enforcement.py)."""
import datetime, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import check_enforcement as CE

GOOD = {"checked": "2026-10-21", "result": "none_found", "sources": [{"label": "x", "url": "https://example.gov/carts"}], "note": "searched"}


class Enforcement(unittest.TestCase):
    def test_every_live_region_has_a_record(self):
        errs = [e for r in CE.live_regions() for e in CE.problems(r, CE.record(r))]
        self.assertEqual(errs, [], "\n".join(errs))

    def test_missing_record_fails(self):
        self.assertTrue(CE.problems("newtown", None))

    def test_good_record_passes(self):
        self.assertEqual(CE.problems("x", GOOD, datetime.date(2026, 10, 21)), [])

    def test_bad_records_fail(self):
        for k, v in (("checked", "yesterday"), ("checked", "2099-01-01"), ("result", "ok"), ("sources", []),
                     ("sources", [{"label": "no link", "url": "map.png"}]), ("note", " ")):
            self.assertTrue(CE.problems("x", {**GOOD, k: v}, datetime.date(2026, 10, 21)), (k, v))
        self.assertTrue(CE.problems("x", {**GOOD, "result": "bans_pending"}, datetime.date(2026, 10, 21)))
        self.assertEqual(CE.problems("x", {**GOOD, "result": "bans_pending", "missing": ["Rd: banned, we show green"]}, datetime.date(2026, 10, 21)), [])

    def test_30a_cites_the_sheriff_map(self):
        urls = [s["url"] for s in CE.record("30a")["sources"]]
        self.assertTrue(any("waltonso.org" in u and "lsv_map" in u for u in urls), urls)


if __name__ == "__main__":
    unittest.main()
