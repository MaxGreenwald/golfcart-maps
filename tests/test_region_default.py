"""Far-away geolocation must stay outside regionAt's 50-mile window.

scripts/test_regions.py used to call 40.7,-74.0 'far away' and expect San Diego.
Greenwich, CT (added with the next-10 regions) is about 30 miles from that point,
inside the window in public/app.js, so the map opens Greenwich. That is the rule,
not a flake. Central Kansas is the far-away fixture. This mirrors regionAt; the
browser check in scripts/test_regions.py is what the app actually does.
"""
import json
import math
import os
import re
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def hav(lng1, lat1, lng2, lat2):
    """Same formula as public/router.js hav. Inputs are lng, lat."""
    radius = 6371000
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlon = (lng2 - lng1) * rad
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(min(1.0, x)))


def threshold_m():
    with open(os.path.join(ROOT, "public", "app.js"), encoding="utf-8") as handle:
        text = handle.read()
    match = re.search(r"function regionAt\(lat,lng\)\{let best=null,bd=(\d+)", text)
    if not match:
        raise AssertionError("regionAt threshold missing from public/app.js")
    return int(match.group(1))


def region_at(lat, lng, regions, limit):
    """Mirror of public/app.js regionAt. None means the loader defaults to San Diego."""
    best = None
    best_d = limit
    for reg in regions:
        if reg.get("hidden"):
            continue
        box = reg["bbox"]
        if lat >= box[0] and lat <= box[2] and lng >= box[1] and lng <= box[3]:
            return reg["id"]
        dist = hav(lng, lat, reg["center"][1], reg["center"][0])
        if dist < best_d:
            best_d = dist
            best = reg["id"]
    return best


def script_constants():
    with open(os.path.join(ROOT, "scripts", "test_regions.py"), encoding="utf-8") as handle:
        text = handle.read()
    nyc = re.search(r"NYC_LAT, NYC_LNG = ([0-9.]+), ([-0-9.]+)", text)
    far = re.search(r"FAR_LAT, FAR_LNG = ([0-9.]+), ([-0-9.]+)", text)
    if not nyc or not far:
        raise AssertionError("NYC_LAT/FAR_LAT missing from scripts/test_regions.py")
    return text, (float(nyc.group(1)), float(nyc.group(2))), (float(far.group(1)), float(far.group(2)))


class RegionDefault(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "public", "data", "regions.json"), encoding="utf-8") as handle:
            self.regions = json.load(handle)
        self.limit = threshold_m()
        self.text, self.nyc, self.far = script_constants()

    def test_threshold_is_fifty_miles(self):
        self.assertEqual(self.limit, 80467)

    def test_old_nyc_point_is_greenwich_not_a_flake(self):
        lat, lng = self.nyc
        self.assertEqual((lat, lng), (40.7, -74.0))
        picked = region_at(lat, lng, self.regions, self.limit)
        self.assertEqual(picked, "greenwich")
        greenwich = next(reg for reg in self.regions if reg["id"] == "greenwich")
        miles = hav(lng, lat, greenwich["center"][1], greenwich["center"][0]) / 1609.344
        self.assertLess(miles, 50)
        self.assertGreater(miles, 20)
        box = greenwich["bbox"]
        inside = lat >= box[0] and lat <= box[2] and lng >= box[1] and lng <= box[3]
        self.assertFalse(inside)
        self.assertIn('geolocation={"latitude":NYC_LAT,"longitude":NYC_LNG}', self.text)
        self.assertIn('ck("NYC area within 50 mi of Greenwich picks greenwich"', self.text)

    def test_far_away_fixture_is_outside_every_region(self):
        lat, lng = self.far
        self.assertEqual((lat, lng), (38.5, -98.5))
        self.assertIsNone(region_at(lat, lng, self.regions, self.limit))
        nearest = min(
            hav(lng, lat, reg["center"][1], reg["center"][0])
            for reg in self.regions
            if not reg.get("hidden")
        )
        self.assertGreater(nearest, self.limit)
        self.assertIn('geolocation={"latitude":FAR_LAT,"longitude":FAR_LNG}', self.text)
        self.assertIn('ck("far away -> San Diego default"', self.text)


if __name__ == "__main__":
    unittest.main()
