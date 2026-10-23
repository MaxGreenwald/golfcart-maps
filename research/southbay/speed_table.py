#!/usr/bin/env python3
"""South Bay LA posted speeds from each city's adopted speed-zone ordinance (and RPV's 2018 General Plan traffic study),
resolved onto OSM geometry. Each row: (city, street, from, to, mph). from/to are cross streets, "limit:N|S|E|W"
(the street's farthest point inside that city in that direction) or None/None (the whole street inside the city).
Writes speed_names entries ("bboxes" = buffered chunks of the resolved stretch) into research/regions/southbay.json.
Rows that can't be resolved are printed and skipped (the road then falls back to DOT/Mapillary/OSM).
usage: python3 research/southbay/speed_table.py   (needs cache/southbay_osm.json)"""
import json, os, re, math, heapq
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
SRC = {
 "MB": ("https://gocodebook.com/library/us/ca/manhattan-beach/title-14-traffic/chapter-14.56-special-speed-zones", "Manhattan Beach Municipal Code ch. 14.56 special speed zones"),
 "HB": ("https://gocodebook.com/library/us/ca/hermosa-beach/title-10-vehicles-and-traffic/chapter-10.40-speed-regulations", "Hermosa Beach Municipal Code 10.40.020 prima facie speed limits (Ord. 23-1466, 2023)"),
 "RB": ("https://ecode360.com/42644243", "Redondo Beach Municipal Code 3-7.503 speed zones"),
 "TOR": ("https://gocodebook.com/library/us/ca/torrance/sections/61.10", "Torrance Municipal Code art. 10, 61.10.1-61.10.5 speed limits"),
 "PVE": ("https://gocodebook.com/library/us/ca/palos-verdes-estates/title-10-vehicles-and-traffic/chapter-10.56-speed-limits", "Palos Verdes Estates Municipal Code 10.56.010 speed limits"),
 "ES": ("https://gocodebook.com/library/us/ca/el-segundo/title-8-vehicles-and-traffic/chapter-4-miscellaneous-traffic-provisions", "El Segundo Municipal Code 8-4-3 special speed zones"),
 "RPV": ("https://www.rpvca.gov/DocumentCenter/View/12638/Traffic-Impact-Report", "Rancho Palos Verdes General Plan traffic study (2018), posted speed limits"),
 "MBN": ("https://www.thembnews.com/2026/03/28/567983/sepulveda-safety-improvements-targeted-for-manhattan-beach", "Manhattan Beach News (Mar 2026): Sepulveda Blvd (SR-1) through Manhattan Beach is 35 mph, kept by Caltrans after a 2023 study"),
 "RPV25": ("https://www.rpvca.gov/CivicSend/ViewMessage/message/267414", "Rancho Palos Verdes: Palos Verdes Drive East switchbacks lowered to 35 mph (Aug 2025)"),
}
CITY = {"MB": "manhattan_beach", "HB": "hermosa_beach", "RB": "redondo_beach", "TOR": "torrance", "PVE": "palos_verdes_estates", "RPV": "rancho_palos_verdes", "RPV25": "rancho_palos_verdes", "MBN": "manhattan_beach", "ES": "el_segundo"}
PCH = r"^(North |South )?Pacific Coast Highway$"
R190 = r"^(West )?190th Street$|^Anita Street/190th Street$"
T = [
 # ---- Manhattan Beach 14.56.010 / .020 ----
 ("MB", "Ardmore Avenue", None, None, 30),
 ("MB", "Aviation Boulevard", None, None, 40),
 ("MB", "Highland Avenue", "Rosecrans Avenue", "45th Street", 30),
 ("MB", "Manhattan Beach Boulevard", "Sepulveda Boulevard", "Aviation Boulevard", 35),
 ("MB", "Manhattan Beach Boulevard", "Sepulveda Boulevard", "Pacific Avenue", 35),
 ("MB", "Manhattan Beach Boulevard", "Pacific Avenue", "Valley Drive", 30),
 ("MB", "Marine Avenue", "Sepulveda Boulevard", "Aviation Boulevard", 35),
 ("MB", "Rosecrans Avenue", "Blanche Road", "Aviation Boulevard", 40),
 ("MB", "Rosecrans Avenue", "Highland Avenue", "Blanche Road", 35),
 ("MB", "Ocean Drive", None, None, 15),
 ("MB", "Valley Drive", "Blanche Road", "15th Street", 25),
 ("MB", "Valley Drive", "Sepulveda Boulevard", "Blanche Road", 30),
 ("MB", "Valley Drive", "Manhattan Beach Boulevard", "limit:S", 30),
 ("MB", "Alma Avenue", "Marine Avenue", "Rosecrans Avenue", 20),
 ("MBN", "Sepulveda Boulevard", None, None, 35),
 # ---- Hermosa Beach 10.40.020 (all other streets 25: see the poly entry) ----
 ("HB", "Ardmore Avenue", "limit:N", "21st Street", 30),
 ("HB", "Ardmore Avenue", "21st Street", "2nd Street", 25),
 ("HB", "Artesia Boulevard", PCH, "limit:E", 35),
 ("HB", "Aviation Boulevard", PCH, "limit:E", 35),
 ("HB", "Hermosa Avenue", "14th Street", "8th Street", 20),
 ("HB", "Hermosa Avenue", None, None, 25),
 ("HB", "Herondo Street", None, None, 30),
 ("HB", PCH, "Artesia Boulevard", "16th Street", 35),
 ("HB", PCH, "16th Street", "limit:S", 30),
 ("HB", "Pier Avenue", PCH, "Ardmore Avenue", 25),
 ("HB", "Pier Avenue", "Ardmore Avenue", "Hermosa Avenue", 20),
 # ---- Redondo Beach 3-7.503 ----
 ("RB", "Catalina Avenue", "Palos Verdes Boulevard", "Avenue I", 20),
 ("RB", "Beland Boulevard", None, None, 25),
 ("RB", "Beryl Street", "Harbor Drive", PCH, 25),
 ("RB", "Esplanade", None, None, 25),
 ("RB", "Flagler Lane", None, None, 25),
 ("RB", "Torrance Boulevard", "Catalina Avenue", PCH, 25),
 ("RB", "182nd Street", "Inglewood Avenue", "Kingsdale Avenue", 25),
 ("RB", "Beryl Street", PCH, "Flagler Lane", 30),
 ("RB", "Camino Real", "Torrance Boulevard", "Juanita Avenue", 30),
 ("RB", "Del Amo Street", None, None, 30),
 ("RB", "Diamond Street", "Catalina Avenue", "Prospect Avenue", 30),
 ("RB", "Emerald Street", "Catalina Avenue", "Prospect Avenue", 30),
 ("RB", "Garnet Street", None, None, 30),
 ("RB", "Grant Avenue", "Inglewood Avenue", "Kingsdale Avenue", 30),
 ("RB", "Harbor Drive", None, None, 30),
 ("RB", "Herondo Street", None, None, 30),
 ("RB", "Palos Verdes Boulevard", None, None, 30),
 ("RB", "Prospect Avenue", PCH, "Palos Verdes Boulevard", 30),
 ("RB", "Ripley Avenue", None, None, 30),
 ("RB", "182nd Street", "Kingsdale Avenue", "Hawthorne Boulevard", 30),
 ("RB", R190, PCH, "Inglewood Avenue", 35),
 ("RB", "Artesia Boulevard", "Aviation Boulevard", "Hawthorne Boulevard", 35),
 ("RB", "Camino Real", "Juanita Avenue", "limit:E", 35),
 ("RB", "Catalina Avenue", "Avenue I", PCH, 35),
 ("RB", "Grant Avenue", "Aviation Boulevard", "Inglewood Avenue", 35),
 ("RB", "Hawthorne Boulevard", "182nd Street", "Redondo Beach Boulevard", 35),
 ("RB", "Inglewood Avenue", R190, "Artesia Boulevard", 35),
 ("RB", PCH, "Palos Verdes Boulevard", R190, 35),
 ("RB", "Prospect Avenue", "Palos Verdes Boulevard", R190, 35),
 ("RB", "Torrance Boulevard", PCH, "limit:E", 35),
 ("RB", "Artesia Boulevard", "Harper Avenue", "Aviation Boulevard", 40),
 ("RB", "Aviation Boulevard", "Artesia Boulevard", "Marine Avenue", 40),
 ("RB", "Inglewood Avenue", "Manhattan Beach Boulevard", "Marine Avenue", 40),
 ("RB", "Manhattan Beach Boulevard", "Aviation Boulevard", "Inglewood Avenue", 40),
 ("RB", "Marine Avenue", "Aviation Boulevard", "Inglewood Avenue", 40),
 ("RB", PCH, "Prospect Avenue", "Palos Verdes Boulevard", 40),
 ("RB", "Redondo Beach Avenue", "Marine Avenue", "Manhattan Beach Boulevard", 40),
 ("RB", R190, "Inglewood Avenue", "Hawthorne Boulevard", 40),
 ("RB", "Inglewood Avenue", "Artesia Boulevard", "Manhattan Beach Boulevard", 45),
 ("RB", PCH, "limit:S", "Prospect Avenue", 45),
 # ---- Torrance 61.10.1 (25) ----
 ("TOR", "Paseo de la Playa", None, None, 25), ("TOR", "Calle Miramar", None, None, 25), ("TOR", "Flagler Lane", None, None, 25),
 ("TOR", "Victor Street", None, None, 25), ("TOR", "Ocean Avenue", "Torrance Boulevard", PCH, 25), ("TOR", "Amie Avenue", None, None, 25),
 ("TOR", "Maple Avenue", "Torrance Boulevard", "Sepulveda Boulevard", 25), ("TOR", "Yukon Avenue", None, None, 25),
 ("TOR", "Arlington Avenue", "Van Ness Avenue", "Carson Street", 25), ("TOR", "Marcelina Avenue", None, None, 25),
 ("TOR", "164th Street", None, None, 25), ("TOR", "166th Street", None, None, 25), ("TOR", "168th Street", None, None, 25),
 ("TOR", "Cherry Avenue", None, None, 25), ("TOR", "171st Street", None, None, 25), ("TOR", "186th Street", None, None, 25),
 ("TOR", "Spencer Street", None, None, 25), ("TOR", "Emerald Street", None, None, 25), ("TOR", "Civic Center Drive", None, None, 25),
 ("TOR", r"^Dominguez St(reet)?$", None, None, 25), ("TOR", "235th Street", "Crenshaw Boulevard", "Western Avenue", 25),
 ("TOR", "Via Valmonte", None, None, 25), ("TOR", "Newton Street", None, None, 25), ("TOR", "Crest Road", None, None, 25),
 # 61.10.2 (30)
 ("TOR", "Palos Verdes Boulevard", "Torrance Boulevard", "limit:W", 30), ("TOR", "Earl Street", None, None, 30),
 ("TOR", r"^Del Amo Circle( East| West| North| South)?$", None, None, 30), ("TOR", "Maple Avenue", "California Street", "Torrance Boulevard", 30),
 ("TOR", "Arlington Avenue", "Carson Street", "Sepulveda Boulevard", 30), ("TOR", "Cabrillo Avenue", None, None, 30),
 ("TOR", "Calle Mayor", "Palos Verdes Boulevard", PCH, 30), ("TOR", "Beryl Street", R190, "Flagler Lane", 30),
 ("TOR", "Plaza del Amo", "Carson Street", "Border Avenue", 30),
 # 61.10.3 (35)
 ("TOR", "Henrietta Street", None, None, 35), ("TOR", "Anza Avenue", R190, "Sepulveda Boulevard", 35),
 ("TOR", "Hawthorne Boulevard", "Redondo Beach Boulevard", R190, 35), ("TOR", "Prairie Avenue", "Redondo Beach Boulevard", R190, 35),
 ("TOR", "Madrona Avenue", "Torrance Boulevard", "Sepulveda Boulevard", 35), ("TOR", "Maple Avenue", "Sepulveda Boulevard", "Nadine Circle", 35),
 ("TOR", "Van Ness Avenue", "Redondo Beach Boulevard", R190, 35), ("TOR", "Arlington Avenue", "Sepulveda Boulevard", "limit:S", 35),
 ("TOR", "182nd Street", "Hawthorne Boulevard", "Western Avenue", 35), ("TOR", R190, "limit:W", "Inglewood Avenue", 35),
 ("TOR", "Del Amo Boulevard", "Madrona Avenue", "Maple Avenue", 35), ("TOR", "Del Amo Boulevard", "Crenshaw Boulevard", "Western Avenue", 35),
 ("TOR", "Maricopa Street", None, None, 35), ("TOR", "Torrance Boulevard", "Madrona Avenue", "Western Avenue", 35),
 ("TOR", "Carson Street", "Palos Verdes Boulevard", "Western Avenue", 35), ("TOR", "Plaza del Amo", "Madrona Avenue", "Crenshaw Boulevard", 35),
 ("TOR", "223rd Street", "Border Avenue", "Western Avenue", 35), ("TOR", "235th Street", "Nadine Circle", "Crenshaw Boulevard", 35),
 ("TOR", "Calle Mayor", PCH, "Anza Avenue", 35), ("TOR", PCH, "limit:W", "Palos Verdes Boulevard", 35), ("TOR", "Vista Montana", None, None, 35),
 ("TOR", "Rolling Hills Road", "Hawthorne Boulevard", "limit:S", 35), ("TOR", "Palos Verdes Boulevard", PCH, "limit:S", 35),
 ("TOR", "182nd Street", "Hawthorne Boulevard", "Kingsdale Avenue", 35), ("TOR", "Maple Avenue", "Del Amo Boulevard", "California Street", 35),
 # 61.10.4 (40)
 ("TOR", "Hawthorne Boulevard", PCH, R190, 40), ("TOR", "Madison Street", None, None, 40), ("TOR", "Prairie Avenue", R190, "Del Amo Boulevard", 40),
 ("TOR", "Madrona Avenue", "Del Amo Boulevard", "Torrance Boulevard", 40), ("TOR", "Crenshaw Boulevard", "Redondo Beach Boulevard", R190, 40),
 ("TOR", "Van Ness Avenue", "Del Amo Boulevard", "Torrance Boulevard", 40), ("TOR", "Western Avenue", "Artesia Boulevard", R190, 40),
 ("TOR", "Western Avenue", "Del Amo Boulevard", "limit:S", 40), ("TOR", "Redondo Beach Boulevard", "Hawthorne Boulevard", "Prairie Avenue", 40),
 ("TOR", "Redondo Beach Boulevard", "Crenshaw Boulevard", "limit:E", 40), ("TOR", "Artesia Boulevard", "Hawthorne Boulevard", "Crenshaw Boulevard", 40),
 ("TOR", R190, "Inglewood Avenue", "Prairie Avenue", 40), ("TOR", "Del Amo Boulevard", "limit:W", "Madrona Avenue", 40),
 ("TOR", "Torrance Boulevard", "limit:W", "Madrona Avenue", 40), ("TOR", "Sepulveda Boulevard", "limit:W", "Maple Avenue", 40),
 ("TOR", "Sepulveda Boulevard", "Arlington Avenue", "Western Avenue", 40), ("TOR", "Lomita Boulevard", "Anza Avenue", "Hawthorne Boulevard", 40),
 ("TOR", PCH, "Palos Verdes Boulevard", "Vista del Parque", 40), ("TOR", "Crenshaw Boulevard", r"^Dominguez St(reet)?$", "Sepulveda Boulevard", 40),
 # 61.10.5 (45); PCH Calle Mayor -> east city limit is 40 northbound / 45 southbound: shown at 45
 ("TOR", "Hawthorne Boulevard", PCH, "limit:S", 45), ("TOR", "Crenshaw Boulevard", R190, r"^Dominguez St(reet)?$", 45),
 ("TOR", "Crenshaw Boulevard", "Sepulveda Boulevard", "limit:S", 45), ("TOR", "Van Ness Avenue", R190, "Del Amo Boulevard", 45),
 ("TOR", "Western Avenue", R190, "Del Amo Boulevard", 45), ("TOR", "Artesia Boulevard", "Crenshaw Boulevard", "Western Avenue", 45),
 ("TOR", R190, "Prairie Avenue", "Western Avenue", 45), ("TOR", "Sepulveda Boulevard", "Maple Avenue", "Arlington Avenue", 45),
 ("TOR", "Lomita Boulevard", "Hawthorne Boulevard", "Crenshaw Boulevard", 45), ("TOR", "Skypark Drive", None, None, 45),
 ("TOR", PCH, "Vista del Parque", "Calle Mayor", 45), ("TOR", PCH, "Calle Mayor", "limit:E", 45),
 # ---- Palos Verdes Estates 10.56.010 ----
 ("PVE", "Granvia Altamira", None, None, 30), ("PVE", "Palos Verdes Drive North", None, None, 35),
 ("PVE", "Palos Verdes Boulevard", None, None, 30), ("PVE", "Palos Verdes Drive West", None, None, 35),
 ("PVE", "Paseo del Campo", None, None, 25), ("PVE", "Paseo del Mar", None, None, 30), ("PVE", "Via Almar", None, None, 25),
 ("PVE", "Via Campesina", "Palos Verdes Drive North", "Via Elevado", 30), ("PVE", "Via Campesina", "Via Elevado", "Via Corta", 25),
 ("PVE", "Via Coronel", None, None, 25), ("PVE", "Via del Monte", None, None, 25), ("PVE", "Via Fernandez", None, None, 25), ("PVE", "Via Zurita", None, None, 25),
 # ---- El Segundo 8-4-3 ----
 ("ES", "Alaska Avenue", None, None, 35), ("ES", "Apollo Street", None, None, 30), ("ES", "Atwood Way", None, None, 35),
 ("ES", "Aviation Boulevard", None, None, 40), ("ES", "Continental Boulevard", None, None, 30), ("ES", "Douglas Street", None, None, 40),
 ("ES", "El Segundo Boulevard", "Main Street", "Sepulveda Boulevard", 35), ("ES", "El Segundo Boulevard", "Sepulveda Boulevard", "limit:E", 40),
 ("ES", "Grand Avenue", None, None, 35), ("ES", "Hawaii Street", None, None, 35), ("ES", "Hughes Way", None, None, 40),
 ("ES", "Imperial Highway", None, None, 40), ("ES", "Lairport Street", None, None, 35), ("ES", "Maple Avenue", None, None, 35),
 ("ES", "Mariposa Avenue", None, None, 40), ("ES", "Nash Street", None, None, 35), ("ES", "Rosecrans Avenue", "limit:W", "Bell Avenue", 35),
 ("ES", "Rosecrans Avenue", "Bell Avenue", "limit:E", 45), ("ES", "Selby Street", None, None, 30), ("ES", "Utah Avenue", None, None, 35),
 ("ES", r"^Vista [Dd]el Mar( Boulevard)?$", None, None, 45), ("ES", "Walnut Avenue", None, None, 30),
 # ---- Rancho Palos Verdes (2018 General Plan traffic study posted limits; only single-value roads) ----
 ("RPV", "Hawthorne Boulevard", None, None, 45), ("RPV", "Palos Verdes Drive West", None, None, 45), ("RPV", "Palos Verdes Drive South", None, None, 45),
 ("RPV", "Crenshaw Boulevard", None, None, 45), ("RPV", "Crest Road", "Hawthorne Boulevard", "Crenshaw Boulevard", 40),
 ("RPV", "Crestridge Road", None, None, 40), ("RPV", "Highridge Road", None, None, 35), ("RPV", "Indian Peak Road", None, None, 35),
 ("RPV", "Miraleste Drive", None, None, 35), ("RPV", "Montemalaga Drive", None, None, 35), ("RPV", "Western Avenue", None, None, 35),
]
ROADS = set("motorway trunk primary secondary tertiary unclassified residential living_street".split())
def rx(n):
    return n if n.startswith("^") else r"^(North |South |East |West )?" + re.escape(n) + "$"
def ring(c):
    gj = json.load(open(os.path.join(ROOT, "research/city_limits", c + ".json")))["geojson"]
    return gj["coordinates"][0] if gj["type"] == "Polygon" else max((p[0] for p in gj["coordinates"]), key=len)
KX, KY = 111320 * math.cos(math.radians(33.83)), 110540
def inside(x, y, r, buf=40):
    c = False
    for i in range(len(r)):
        (x1, y1), (x2, y2) = r[i - 1][:2], r[i][:2]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    if c or not buf: return c
    for i in range(len(r)):
        (x1, y1), (x2, y2) = r[i - 1][:2], r[i][:2]
        ax, ay, bx, by, px, py = x1*KX, y1*KY, x2*KX, y2*KY, x*KX, y*KY
        vx, vy = bx-ax, by-ay; L = vx*vx + vy*vy; u = max(0, min(1, ((px-ax)*vx + (py-ay)*vy) / L)) if L else 0
        if math.hypot(px-ax-u*vx, py-ay-u*vy) < buf: return True
    return False
def main():
    d = json.load(open(os.path.join(ROOT, "cache/southbay_osm.json")))["elements"]
    ways = [w for w in d if w["tags"].get("highway") in ROADS and (w["tags"].get("name") or w["tags"].get("ref"))]
    def named(r):
        c = re.compile(r, re.I)
        return [w for w in ways if c.search(w["tags"].get("name", "")) or c.search(w["tags"].get("ref", ""))]
    key = lambda q: (round(q["lat"], 7), round(q["lon"], 7))
    groups, bad = {}, []
    rings = {}
    for city, st, a, b, mph in T:
        for BUF in (120, 300):   # retry a from/to stretch with a wider city-line buffer only if the 120 m try failed
            if BUF == 300:
                if not (bad and bad[-1][:5] == (city, st, a, b, mph)): break
                bad.pop()
            cr = rings.setdefault(CITY[city], ring(CITY[city]))
            sw = named(rx(st))
            G = {}
            for w in sw:
                g = w["geometry"]
                for k in range(len(g) - 1):
                    p, q = key(g[k]), key(g[k+1])
                    bf = 40 if a is None else BUF   # a from/to stretch may run along the city line; its ends bound it
                    if not (inside(p[1], p[0], cr, bf) or inside(q[1], q[0], cr, bf)): continue
                    dd = math.hypot((p[0]-q[0])*KY, (p[1]-q[1])*KX)
                    G.setdefault(p, []).append((q, dd)); G.setdefault(q, []).append((p, dd))
            if not G: bad.append((city, st, a, b, mph, "street not found in city")); continue
            def ends(e):
                if e.startswith("limit:"):
                    dr = e[6:]; f = {"N": lambda p: p[0], "S": lambda p: -p[0], "E": lambda p: p[1], "W": lambda p: -p[1]}[dr]
                    m = max(f(p) for p in G); return {p for p in G if f(p) >= m - 0.0003}
                cn, near = set(), []
                for w in named(rx(e)):
                    for q in w["geometry"]:
                        if key(q) in G: cn.add(key(q))
                        near.append(key(q))
                if not cn:   # offset / T junction without a shared node: street nodes within 30 m of the cross street
                    cn = {p for p in G if any(math.hypot((p[0]-q[0])*KY, (p[1]-q[1])*KX) < 60 for q in near)}
                return cn
            if a is None: paths = [[p for p in G]]; pts = paths[0]; segs = [(p, q) for p in G for q, _ in G[p]]
            else:
                A, B = ends(a), ends(b)
                if not A or not B: bad.append((city, st, a, b, mph, "no node for " + ("from" if not A else "to"))); continue
                dist = {p: 0 for p in A}; prev = {}; h = [(0, p) for p in A]; heapq.heapify(h); hit = None
                while h:
                    dd, p = heapq.heappop(h)
                    if dd > dist.get(p, 1e18): continue
                    if p in B: hit = p; break
                    for q, l in G[p]:
                        if dd + l < dist.get(q, 1e18): dist[q] = dd + l; prev[q] = p; heapq.heappush(h, (dd + l, q))
                if hit is None: bad.append((city, st, a, b, mph, "no path")); continue
                path = [hit]
                while path[-1] in prev: path.append(prev[path[-1]])
                segs = list(zip(path, path[1:]))
            # chunk the stretch's edges into ~250 m boxes, padded ~30 m
            boxes, cur, L = [], [], 0
            for p, q in segs:
                cur += [p, q]; L += math.hypot((p[0]-q[0])*KY, (p[1]-q[1])*KX)
                if L > 250: boxes.append(cur); cur, L = [], 0
            if cur: boxes.append(cur)
            bb = [[round(min(p[0] for p in c) - 0.00027, 5), round(min(p[1] for p in c) - 0.00032, 5), round(max(p[0] for p in c) + 0.00027, 5), round(max(p[1] for p in c) + 0.00032, 5)] for c in boxes]
            # merge identical boxes
            bb = [list(x) for x in sorted({tuple(x) for x in bb})]
            url, lab = SRC[city]
            desc = st if not st.startswith("^") else re.sub(r"[\^\$\(\)\?]|\|.*", "", st).replace("North |South ", "").replace("West ", "").strip()
            rng = "whole street in city" if a is None else "%s to %s" % (re.sub(r"[\^\$\(\)\?]|\|.*", "", a).replace("North |South ", "").replace("West ", ""), re.sub(r"[\^\$\(\)\?]|\|.*", "", b).replace("North |South ", "").replace("West ", ""))
            groups.setdefault((rx(st), mph, city), {"names": rx(st), "mph": mph, "url": url, "label": "%s: %s (%s) %d mph" % (lab, desc, rng, mph), "highway": "^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street)(_link)?$", "bboxes": []})["bboxes"] += bb
    out = sorted(groups.values(), key=lambda o: -o["mph"])   # overlapping boxes at zone ends: the higher limit wins (safe side)
    for o in out: o["bboxes"] = [list(x) for x in sorted({tuple(x) for x in o["bboxes"]})]
    return out, bad
if __name__ == "__main__":
    out, bad = main()
    for x in bad: print("UNRESOLVED", x)
    print(len(out), "entries", sum(len(o["bboxes"]) for o in out), "boxes")
    json.dump(out, open("/tmp/sb_speed_names.json", "w"), indent=1)
