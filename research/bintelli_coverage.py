#!/usr/bin/env python3
"""Bintelli store + dealer coverage vs Golf Cart Maps regions (2026-10-23).

Sources (public, fetched 2026-10-23 PT, snapshots in research/bintelli_raw/):
  own stores: https://www.bintelligolfcarts.com/wp-admin/admin-ajax.php?action=asl_load_stores&load_all=1&layout=1
              (the Agile Store Locator feed behind bintelligolfcarts.com "Our Locations")
  dealers:    https://www.bintelli.com/wp-admin/admin-ajax.php?action=asl_load_stores&load_all=1&layout=1
              (the same plugin feed on bintelli.com; the visible /find-a-dealer/ page is a lead form)
Coverage: great-circle distance from the location to the nearest live region's bbox in public/data/regions.json.
  covered <= 10 mi, partly <= 25 mi, else gap.
Outputs: research/bintelli_coverage_2026-10-23.{csv,md} and the page data JSON (path passed with --page-json).
"""
import csv, html, json, math, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "research", "bintelli_raw")
OWN_SRC = "https://www.bintelligolfcarts.com/wp-admin/admin-ajax.php?action=asl_load_stores&load_all=1&layout=1"
DLR_SRC = "https://www.bintelli.com/wp-admin/admin-ajax.php?action=asl_load_stores&load_all=1&layout=1"
COVERED, PARTLY = 10.0, 25.0
OWN_MARKET = {"314": "Charleston, SC", "298": "Charleston, SC", "299": "Myrtle Beach, SC", "554": "Myrtle Beach, SC",
              "550": "The Villages, FL", "528": "Sarasota, FL", "541": "Largo / Clearwater, FL", "529": "Fort Myers, FL",
              "536": "Nocatee / Ponte Vedra, FL", "534": "Daytona (Holly Hill / Ormond), FL", "544": "Orlando (Casselberry), FL",
              "535": "Pompano Beach, FL", "504": "Peachtree City, GA", "512": "Duluth (Atlanta), GA",
              "503": "Greenville, SC", "553": "Virginia Beach, VA", "549": "The Woodlands, TX"}

def miles(a, b, c, d):
    p = math.pi / 180
    h = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))

def to_bbox(lat, lon, bb):
    s, w, n, e = bb
    return miles(lat, lon, min(max(lat, s), n), min(max(lon, w), e))

def nearest(lat, lon, regions):
    best = min(regions, key=lambda r: to_bbox(lat, lon, r["bbox"]))
    d = to_bbox(lat, lon, best["bbox"])
    status = "covered" if d <= COVERED else "partly" if d <= PARTLY else "gap"
    return best, round(d, 1), status

def clean(s): return html.unescape(s or "").strip()

def norm_title(t): return re.sub(r"\s*\((off-road|off road)\)\s*", "", clean(t), flags=re.I).strip()

def load():
    regions = json.load(open(os.path.join(ROOT, "public", "data", "regions.json")))
    own = json.load(open(os.path.join(RAW, "bintelligolfcarts_com_asl_load_stores.json")))
    allr = json.load(open(os.path.join(RAW, "bintelli_com_asl_load_stores.json")))
    rows = []
    for x in own:
        rows.append(dict(kind="own_store", id="bgc-" + x["id"], name=clean(x["title"]), street=clean(x["street"]), city=clean(x["city"]),
                         state=clean(x["state"]).replace("Florida", "FL"), lat=float(x["lat"]), lon=float(x["lng"]), market=OWN_MARKET[x["id"]],
                         source=OWN_SRC, website=clean(x["website"])))
    seen = set()
    for x in allr:
        t = norm_title(x["title"])
        if re.match(r"(?i)bintelli (golf carts|powersports)", t):   # company-owned stores, already in the own list
            continue
        key = (t.lower(), round(float(x["lat"]), 3), round(float(x["lng"]), 3))
        if key in seen: continue                                      # same dealer listed again as "(Off-Road)"
        seen.add(key)
        st = clean(x["state"]) or ""
        country = clean(x["country"]) or ("United States" if st not in ("Bahamas", "Ontario") else "")
        if st == "Iowa": st = "IA"
        if st == "Amsterdam": st = "NY"   # Amsterdam, NY (state field holds the city)
        if x["id"] == "679": st = "NC"
        if not st and "Puerto" in country: st = "PR"    # Coastal Motorsports, Beaufort NC (state field empty)
        rows.append(dict(kind="dealer", id="bin-" + x["id"], name=t, street=clean(x["street"]), city=clean(x["city"]), state=st,
                         country=country, lat=float(x["lat"]), lon=float(x["lng"]), market="", source=DLR_SRC, website=clean(x["website"])))
    for r in rows:
        reg, d, s = nearest(r["lat"], r["lon"], regions)
        r.update(nearest_region=reg["name"], nearest_region_slug=reg["slug"], miles_to_region=d, coverage=s)
    # dealer markets: covered/partly -> the region; gaps -> greedy 30-mi clusters named after the first city
    gaps = [r for r in rows if r["kind"] == "dealer"]
    for r in gaps:
        if r["coverage"] != "gap": r["market"] = reg_market(r)
    centers = []
    for r in sorted((r for r in gaps if r["coverage"] == "gap"), key=lambda r: (r["state"], r["city"])):
        for c in centers:
            if miles(r["lat"], r["lon"], c[0], c[1]) <= 30: r["market"] = c[2]; break
        else:
            name = f"{r['city']}, {r['state']}" if r["state"] not in ("Bahamas", "Ontario", "Puerto Rico") else f"{r['city']}, {r['state'] or r['country']}"
            if r["state"] == "" and "Puerto" in r.get("country", ""): name = f"{r['city']}, PR"
            centers.append((r["lat"], r["lon"], name)); r["market"] = name
    return regions, rows

def reg_market(r): return f"{r['nearest_region']} area"

def pct(rows, ok):
    return round(100.0 * sum(r["coverage"] in ok for r in rows) / len(rows), 1) if rows else 0.0

def summarize(rows):
    out = {}
    for kind in ("own_store", "dealer"):
        rs = [r for r in rows if r["kind"] == kind]
        mk = {}
        for r in rs: mk.setdefault(r["market"], []).append(r)
        rank = {"covered": 0, "partly": 1, "gap": 2}
        markets = [dict(market=m, n=len(v), coverage=min((x["coverage"] for x in v), key=rank.get),
                        nearest_region=min(v, key=lambda x: x["miles_to_region"])["nearest_region"],
                        miles=min(x["miles_to_region"] for x in v), states=sorted({x["state"] for x in v})) for m, v in mk.items()]
        markets.sort(key=lambda m: (rank[m["coverage"]], m["miles"]))
        out[kind] = dict(n=len(rs), covered=sum(r["coverage"] == "covered" for r in rs), partly=sum(r["coverage"] == "partly" for r in rs),
                         gap=sum(r["coverage"] == "gap" for r in rs), pct_covered=pct(rs, {"covered"}), pct_covered_or_partly=pct(rs, {"covered", "partly"}),
                         markets=markets, n_markets=len(markets),
                         mkt_pct_covered=round(100.0 * sum(m["coverage"] == "covered" for m in markets) / len(markets), 1),
                         mkt_pct_covered_or_partly=round(100.0 * sum(m["coverage"] != "gap" for m in markets) / len(markets), 1))
    return out

if __name__ == "__main__":
    regions, rows = load()
    S = summarize(rows)
    stamp = "2026-10-23"
    with open(os.path.join(ROOT, "research", f"bintelli_coverage_{stamp}.csv"), "w", newline="") as f:
        cols = ["kind", "market", "name", "street", "city", "state", "lat", "lon", "coverage", "nearest_region", "miles_to_region", "website", "source", "id"]
        w = csv.DictWriter(f, cols, extrasaction="ignore"); w.writeheader()
        for r in sorted(rows, key=lambda r: (r["kind"] != "own_store", r["market"], r["name"])): w.writerow(r)
    if "--page-json" in sys.argv:
        p = sys.argv[sys.argv.index("--page-json") + 1]
        pub = [dict(k=r["kind"][0], n=r["name"], c=f"{r['city']}, {r['state']}", la=round(r["lat"], 5), lo=round(r["lon"], 5), s=r["coverage"],
                    m=r["market"], rg=r["nearest_region"], mi=r["miles_to_region"]) for r in rows]
        regs = [dict(n=r["name"], s=r["slug"], b=r["bbox"]) for r in regions]
        json.dump(dict(date=stamp, summary=S, points=pub, regions=regs), open(p, "w"), separators=(",", ":"))
    json.dump(S, open("/tmp/bintelli_summary.json", "w"), indent=1)
    for k in S: print(k, {x: S[k][x] for x in S[k] if x != "markets"})
