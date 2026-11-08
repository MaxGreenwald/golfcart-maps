"""Nov 8 2026 Street View speed signs on the 24 new towns.

Source code 's' is a posted sign read in Street View. It records the speed on the
segments that sign governs. It does not lift a ban (flag 1 or flag 4) and it
does not replace a conflicting Mapillary zone that the sign was not placed on.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tile(slug, name):
    with open(os.path.join(ROOT, "public", "data", slug, "tiles", name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def index(slug):
    with open(os.path.join(ROOT, "public", "data", slug, "index.json"), encoding="utf-8") as fh:
        return json.load(fh)


def src(slug, seg):
    sources = index(slug)["sources"]
    return sources[seg[8]]


class StreetViewNov8(unittest.TestCase):
    def test_source_code_s_cites_the_photo_and_does_not_say_verified(self):
        cases = [
            ("surfside", "-954_289", 303, 40, "B5-072.jpg"),
            ("dadecity", "-823_283", 696, 45, "B5-021.jpg"),
            ("crystalriver", "-826_288", 553, 40, "B5-172.jpg"),
            ("pinehurst", "-795_351", 793, 35, "B5-032.jpg"),
        ]
        for slug, name, row, mph, photo in cases:
            seg = tile(slug, name)[row]
            self.assertEqual(seg[2], mph, (slug, row))
            self.assertEqual(seg[3], "s", (slug, row))
            url, label = src(slug, seg)
            self.assertIn("google.com/maps/@", url)
            self.assertIn("Street View check Nov 8 2026", label)
            self.assertIn(photo, label)
            self.assertNotIn("\u2014", label)
            self.assertNotIn("verified", label.lower())

    def test_fort_king_keeps_the_golf_cart_ban_south_of_the_hospital(self):
        segs = tile("dadecity", "-823_283")
        for row in (696, 695, 694, 698, 697, 693, 692, 691):
            seg = segs[row]
            self.assertEqual(seg[2], 45, row)
            self.assertEqual(seg[3], "s", row)
            self.assertEqual(seg[9], 4, row)
            self.assertEqual(seg[10], 0, row)
        for row in (526, 525, 524, 523, 522, 521, 520, 519, 518):
            self.assertEqual(segs[row][2:4], [25, "i"], row)
            self.assertEqual(segs[row][9], 4, row)

    def test_baldwin_40_is_only_the_bridge_and_the_piece_past_the_sign(self):
        segs = tile("surfside", "-954_289")
        self.assertEqual(segs[184][2:4], [99, "i"])
        self.assertEqual(segs[303][2:4], [40, "s"])
        self.assertEqual(segs[302][2:4], [40, "s"])

    def test_crystal_river_40_is_eastbound_from_the_sign(self):
        segs = tile("crystalriver", "-826_288")
        self.assertEqual(segs[552][2:4], [99, "i"])
        for row in (553, 554, 555, 556, 557, 558, 559):
            self.assertEqual(segs[row][2:4], [40, "s"], row)
            self.assertEqual(segs[row][4], 1, row)
        for row in (900, 901, 902, 903, 904, 905, 906):
            self.assertEqual(segs[row][2:4], [99, "i"], row)

    def test_midland_35_is_only_east_of_the_sign_on_the_eastbound_side(self):
        west = tile("pinehurst", "-795_351")
        east = tile("pinehurst", "-795_352")
        for row in (790, 791, 792):
            self.assertEqual(west[row][2:4], [99, "i"], row)
        self.assertEqual(west[793][2:4], [35, "s"])
        self.assertEqual(east[448][2:4], [35, "s"])
        self.assertEqual(east[449][2:4], [35, "s"])
        self.assertEqual(east[656][2:4], [35, "s"])
        self.assertEqual(len(west[793]), 9)
        self.assertEqual(east[446][2:4], [99, "i"])

    def test_holds_are_unchanged(self):
        # James Way keeps the Mapillary 45 pieces.
        pismo = tile("pismo", "-1207_351")
        james = index("pismo")
        n45 = 0
        for seg in pismo:
            if james["names"][seg[0]] != "James Way":
                continue
            if seg[2] == 45:
                n45 += 1
                self.assertEqual(seg[3], "m")
        self.assertEqual(n45, 5)
        # North Highland ban stays 99 / v / flag 1.
        banned = 0
        for name in ("-817_288", "-817_287"):
            ix = index("mountdora")
            for seg in tile("mountdora", name):
                if ix["names"][seg[0]] != "North Highland Street":
                    continue
                if len(seg) > 9 and seg[9] == 1:
                    banned += 1
                    self.assertEqual(seg[2:4], [99, "v"])
        self.assertEqual(banned, 9)
        # US 98 Alt stays the untagged fast default.
        fairhope = index("fairhope")
        alt = [s for s in tile("fairhope", "-879_305") if fairhope["names"][s[0]] == "United States Highway 98 (Alt)"]
        self.assertEqual([(s[2], s[3]) for s in alt], [(99, "i")])
        # Page Road stays 25 and the golf-cart-only ban.
        pine = index("pinehurst")
        page = []
        for name in ("-795_351", "-795_352"):
            page += [s for s in tile("pinehurst", name) if pine["names"][s[0]] == "Page Road"]
        self.assertTrue(page)
        self.assertTrue(all(s[2] == 25 and s[3] == "i" and s[9] == 4 for s in page))
        # Ocean Highway stays Mapillary 45.
        ocean = [s for s in tile("georgetown", "-793_333") if index("georgetown")["names"][s[0]] == "Ocean Highway"]
        self.assertEqual([(s[2], s[3]) for s in ocean], [(45, "m"), (45, "m"), (45, "m")])
        # North Central stays Mapillary 30. 12th Street stays Mapillary 20.
        central = [s for s in tile("flaglerbeach", "-812_294") + tile("flaglerbeach", "-812_295")
                   if index("flaglerbeach")["names"][s[0]] == "North Central Avenue"]
        self.assertTrue(central)
        self.assertTrue(all(s[2] == 30 and s[3] == "m" for s in central))
        twelfth = []
        ap = index("apalachicola")
        for name in ("-851_297", "-850_297"):
            twelfth += [s for s in tile("apalachicola", name) if ap["names"][s[0]] == "12th Street" and s[3] == "m"]
        self.assertEqual(len(twelfth), 23)
        self.assertTrue(all(s[2] == 20 for s in twelfth))
        # Morro Bay Main Street keeps the 30 and 35 Mapillary zones.
        main = [s for s in tile("morrobay", "-1209_353") if index("morrobay")["names"][s[0]] == "Main Street"]
        self.assertEqual(sum(1 for s in main if s[2] == 30 and s[3] == "m"), 32)
        self.assertEqual(sum(1 for s in main if s[2] == 35 and s[3] == "m"), 6)


if __name__ == "__main__":
    unittest.main()
