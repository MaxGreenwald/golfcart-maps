"""SD safety cautions (Oct 18 2026): stretches where a dated sign photo shows a higher posted limit use that limit, and
OSM-only disagreements keep the official value. Both carry a label the app's CAU list matches. Run: python3 -m unittest discover -s tests"""
import glob, json, os, re, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = os.path.join(ROOT, "public", "data", "sd")


def load():
    idx = json.load(open(os.path.join(D, "index.json")))
    segs = [s for f in sorted(glob.glob(os.path.join(D, "tiles", "*.json"))) for s in json.load(open(f))]
    lab = lambda s: idx["sources"][s[8]][1] if len(s) > 8 and isinstance(s[8], int) else ""
    return idx, segs, lab


class SafetyCaution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idx, cls.segs, lab = load(); cls.lab = staticmethod(lab)
        js = open(os.path.join(ROOT, "public", "app.js"), encoding="utf-8").read()
        cls.cau = re.findall(r"\{src:'([^']+)',text:'([^']+)'\}", js[js.index("const CAU="):js.index("function advOf")])

    def named(self, name):
        return [s for s in self.segs if self.idx["names"][s[0]] == name]

    def test_every_caution_matches_data(self):
        self.assertEqual(len(self.cau), 7)   # 4 SD cautions (Oct 18 2026) + 3 Del Mar ordinance stretches (Nov 19 2026)
        for src, text in self.cau:
            hits = [s for s in self.segs if src in self.lab(s)]
            self.assertTrue(hits, f"no segment carries caution label {src!r}")
            self.assertIn("Check posted signs", text)
            self.assertTrue(all(s[3] == "v" and s[2] <= 35 for s in hits), src)   # advOf only flags sourced, <=35 segments

    def test_la_jolla_blvd_loring_colima_is_35(self):
        # Mapillary sign photos Jan 8 2025 (35 northbound at 32.81046,-117.2661; 35 at 32.80539,-117.25887) + OSM 35.
        corr = [s for s in self.named("La Jolla Boulevard") if 32.8050 <= (s[7][0][1] + s[7][-1][1]) / 2 <= 32.8110 and s[7][0][0] > -117.27]
        self.assertGreater(len(corr), 30)
        self.assertEqual({s[2] for s in corr}, {35}, "Loring St - Colima St must show the posted 35, not 25")
        self.assertTrue(all("Loring St - Colima St: posted 35" in self.lab(s) for s in corr))

    def test_mission_blvd_santa_clara_loring_is_30(self):
        hit = [s for s in self.named("Mission Boulevard") if "Santa Clara Pl - Loring St" in self.lab(s)]
        self.assertGreater(len(hit), 100)
        self.assertEqual({s[2] for s in hit}, {30})
        # the Wilbur Ave sign photo location is inside the stretch
        self.assertTrue(any(abs(s[7][0][1] - 32.8038) < 0.0006 for s in hit))

    def test_lomas_santa_fe_osm50_ways_flagged_not_changed(self):
        hit = [s for s in self.named("Lomas Santa Fe Drive") if "(at Hwy 101:" in self.lab(s)]
        self.assertEqual(len(hit), 4)
        self.assertEqual({s[2] for s in hit}, {35})
        self.assertTrue(all(-117.2720 < s[7][0][0] < -117.2709 for s in hit))

    def test_del_mar_ordinance_stretches_cautioned_speeds_unchanged(self):
        # Del Mar ordinance (Clerk's File 904-4) took effect Nov 19 2026; new signs not confirmed, so no-expiry caution.
        # The caution is presentation only: speeds stay the ordinance values and every segment stays sourced and <= 35.
        want = {"Camino del Mar (Via de la Valle - San Dieguito Bridge": ("Camino del Mar", 30, 10, "from 40 to 30 mph"),
                "Jimmy Durante Blvd (Fairgrounds Gate 2 - San Dieguito Dr": ("Jimmy Durante Boulevard", 30, 35, "from 45 to 30 mph"),
                "Via de la Valle (Camino del Mar - Jimmy Durante Blvd": ("Via de la Valle", 35, 23, "from 40 to 35 mph")}
        cau = dict(self.cau)
        for src, (name, mph, n, frag) in want.items():
            self.assertIn(src, cau, f"no caution for {src!r}")
            self.assertIn("new signs may not be up yet. Check posted signs.", cau[src])
            self.assertIn(frag + " on Nov 19, 2026", cau[src])
            hit = [s for s in self.segs if src in self.lab(s)]
            self.assertEqual(len(hit), n, src)
            self.assertEqual({self.idx["names"][s[0]] for s in hit}, {name})
            self.assertEqual({s[2] for s in hit}, {mph}, src)
            self.assertEqual({s[3] for s in hit}, {"v"}, src)
        js = open(os.path.join(ROOT, "public", "app.js"), encoding="utf-8").read()
        for gone in ("ADV_UNTIL", "drops to", "until Nov 19, 2026"):   # the expired time-boxed warning must not come back
            self.assertNotIn(gone, js)

    def test_cleared_roads_unchanged(self):
        # Prospect St: the Mapillary "35" is a parking sign (photo Jan 10 2025); city business district 25 (R-316675 Table 3).
        p = [s for s in self.named("Prospect Street") if abs(s[7][0][1] - 32.8478) < 0.001 and s[3] == "v"]
        self.assertTrue(p) ; self.assertEqual({s[2] for s in p}, {25})
        # Cardiff S Coast Hwy: 45/40 sign photos are 2017-2019; 35 in Oct 2023; Street View 30 in 2025 (Max).
        c = [s for s in self.named("South Coast Highway") if "Swami's - San Elijo bridge" in self.lab(s)]
        self.assertTrue(c); self.assertEqual({s[2] for s in c}, {30})


if __name__ == "__main__":
    unittest.main()
