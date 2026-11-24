"""Galveston, TX: road status follows City Ord. 21-023 (Code Sec. 34-203) and the Chapter 34 speed schedule.

Sources (extracts in research/galveston_ordinance/):
  Ord. 21-023 https://www.galvestontx.gov/DocumentCenter/View/12508/Golf-Cart-Ordinance-June-2021
  Code Ch. 34 Sec. 34-56/34-58/34-59 https://galvestontx.gov/DocumentCenter/View/11414/Chapter_34___TRAFFIC

Open: Seawall Blvd 6th St to 61st St (34-58(a)(3), 35 mph; not a listed state highway), 6th St, 14th, 21st, 29th,
37th, 53rd, 81st Streets, Market St, Stewart Rd, Jones Dr (34-56 urban default 30 mph, 34-58(a)(6)/(7) 35 mph).
Closed: Broadway, Harborside, Ferry Rd, 61st St, Teichman, Seawall east of 6th St and west of 61st St,
Avenue O 53rd to 15th, Avenue P (Bernardo De Galvez Ave) 19th to 53rd, Park Road 66 (34-203(b)), plus streets
the speed schedule puts over 35 mph (Seawolf Pkwy, Bradner, 9/10 Mile Rd, Apffel Park Rd past Lakeside Dr).
"""
import glob, json, math, os, re, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SIXTH_LON, SIXTY_FIRST_LON = -94.77253, -94.82627   # Seawall junctions with 6th St and 61st St


def J(p):
    return json.load(open(os.path.join(ROOT, p)))


IDX = J("public/data/galveston/index.json")
NAMES, SOURCES = IDX["names"], IDX["sources"]
SEGS = [(NAMES[s[0]], s) for f in glob.glob(os.path.join(ROOT, "public/data/galveston/tiles/*.json")) for s in json.load(open(f))]
RULES = J("public/data/rules.json")["TX"]
REG = next(r for r in J("public/data/regions.json") if r["id"] == "galveston")


def legal(s, cap):
    """Mirror of public/roadrule.js cls(): 0/1 = allowed, 3 = forbidden."""
    if s[3] == "c":
        return True
    if len(s) > 9 and s[9] == 1 and re.match("motorway|trunk|primary", s[1]):
        return False
    return s[2] is not None and s[2] <= cap


def mid(s):
    a, b = s[7][0], s[7][-1]
    return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]


def miles(s):
    return sum(math.hypot((b[0] - a[0]) * math.cos(math.radians(a[1])) * 69.17, (b[1] - a[1]) * 69.17) for a, b in zip(s[7], s[7][1:]))


def pick(name_re, lon_min=-180.0, lon_max=180.0, lat_min=-90.0, lat_max=90.0, hw=None):
    out = [s for n, s in SEGS if re.search(name_re, n) and lon_min < mid(s)[0] < lon_max and lat_min < mid(s)[1] < lat_max
           and (hw is None or re.search(hw, s[1]))]
    assert out, name_re
    return out


class GalvestonOrdinance(unittest.TestCase):
    CAPS = [RULES["lsv"]["max_posted"], RULES["golf_cart"]["max_posted"]]

    def assertAll(self, segs, want, what):
        for cap in self.CAPS:
            bad = [(s[2], s[3], mid(s)) for s in segs if legal(s, cap) != want]
            self.assertEqual(bad, [], f"{what}: expected {'legal' if want else 'closed'} at cap {cap}")

    def test_no_region_default_change(self):
        self.assertNotIn("rule", REG)
        self.assertEqual(self.CAPS, [35, 35])

    def test_seawall_open_6th_to_61st(self):
        s = pick(r"^Seawall Boulevard$", SIXTY_FIRST_LON + 0.0001, SIXTH_LON - 0.0001)
        self.assertGreater(sum(map(miles, s)), 4.0)
        self.assertAll(s, True, "Seawall 6th to 61st")
        for x in s:
            self.assertIn("34-58(a)(3)", SOURCES[x[8]][1])
            self.assertIn("galvestontx.gov", SOURCES[x[8]][0])

    def test_seawall_closed_east_of_6th_and_west_of_61st(self):
        self.assertAll(pick(r"^Seawall Boulevard$", lon_min=SIXTH_LON + 0.0001), False, "Seawall east of 6th")
        self.assertAll(pick(r"^Seawall Boulevard$", lon_max=SIXTY_FIRST_LON - 0.0001), False, "Seawall west of 61st")

    def test_marks_streets_open(self):
        for road, min_mi in [(r"^37th Street$", 1.6), (r"^Martin Luther King Boulevard - 29th Street$", 1.4),
                             (r"^Moody Avenue - 21st Street$", 1.2), (r"^14th Street$", 0.9), (r"^Market Street$", 1.6),
                             (r"^University Boulevard - 6th Street$", 0.9), (r"^Mary Moody Northern Boulevard - 53rd Street$", 1.7),
                             (r"^Jones Drive$", 0.9), (r"^81st Street$", 0.6)]:
            s = [x for x in pick(road) if x[1] != "primary"]
            if road.startswith("^University"):
                s = [x for x in s if mid(x)[1] < 29.3122]   # south of Harborside Dr
            self.assertAll(s, True, road)
            self.assertGreater(sum(map(miles, s)), min_mi, road)
        self.assertAll(pick(r"^Stewart Road$", -94.8505, -94.828), True, "Stewart Rd 61st to 85th and east of 61st")

    def test_banned_roads_closed(self):
        for road in [r"^Broadway", r"^Harborside Drive$", r"^Ferry Road$", r"^61st Stre?e?t$", r"^Teichman Road$",
                     r"^Park Road 66$", r"^Pelican Island Causeway$", r"^Bradner Road$"]:
            self.assertAll(pick(road), False, road)

    def test_avenue_o_p_ranges(self):
        self.assertAll(pick(r"^Avenue O$", -94.8243, -94.7807), False, "Avenue O 53rd to 15th")
        self.assertAll(pick(r"^(Avenue P|Bernardo De Galvez Avenue)$", -94.8237, -94.7848), False, "Avenue P 19th to 53rd")
        self.assertAll(pick(r"^Avenue O$", -94.8280, -94.8244), True, "Avenue O just west of 53rd")
        self.assertAll(pick(r"^Bernardo De Galvez Avenue$", -94.7847, -94.783), True, "Avenue P east of 19th")

    def test_speed_schedule_over_35_closed(self):
        self.assertAll(pick(r"^Seawolf Parkway$", lon_min=-94.8078), False, "Seawolf Pkwy from Bradner")
        self.assertAll(pick(r"^9 Mile Road$", lat_min=29.2332), False, "9 Mile Rd north of Stewart")
        self.assertAll(pick(r"^10 Mile Road$", lat_min=29.2277), False, "10 Mile Rd north of Stewart")
        self.assertAll(pick(r"^Apffel Park Road$", lon_min=-94.7586), False, "Apffel Park Rd past Lakeside Dr")
        self.assertAll(pick(r"^Apffel Park Road$", lon_max=-94.7586), True, "Apffel Park Rd Seawall to Lakeside Dr")

    def test_every_change_cites_a_section(self):
        cfg = J("research/regions/galveston.json")
        for o in cfg["bans"] + cfg["speed_names"] + cfg["overrides"]:
            self.assertRegex(o["label"], r"Sec\. 34-\d+", o["label"])
            self.assertIn("galvestontx.gov", o["url"])
            self.assertNotIn("\u2014", o["label"])


if __name__ == "__main__":
    unittest.main()
