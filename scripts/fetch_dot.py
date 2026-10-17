#!/usr/bin/env python3
"""Pull state DOT / FHWA posted speed-limit polylines for a region bbox -> cache/<id>_dot.json
[{mph, label, url, coords:[[lon,lat],...]}]. usage: fetch_dot.py <region_id> ..."""
import json, sys, urllib.request, urllib.parse, time, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
SRC = {
 "FL": ("https://services1.arcgis.com/O1JpcwDW8sjYuddV/arcgis/rest/services/Maximum_Speed_Limit_TDA/FeatureServer/0", "SPEED", "ROADWAY", "FDOT Maximum Speed Limit (TDA)", "https://gis-fdot.opendata.arcgis.com/datasets/maximum-speed-limit-tda"),
 "TX": ("https://services.arcgis.com/KTcxiTD9dsQw4r7Z/arcgis/rest/services/TxDOT_Speed_Limits/FeatureServer/0", "SPD_LMT", "RTE_NM", "TxDOT Speed Limits", "https://gis-txdot.opendata.arcgis.com/datasets/txdot-speed-limits"),
 "SC": ("https://gis.scdot.org/hosting/rest/services/Speed_Limits/FeatureServer/16", "Regulatory", "RouteLRS", "SCDOT Speed Limits", "https://gis.scdot.org/hosting/rest/services/Speed_Limits/FeatureServer/16"),
 "ME": ("https://gis.maine.gov/mapservices/rest/services/dot/MaineDOT_OpenData/MapServer/34", "speed", "report_id", "MaineDOT Posted Speed Limits (speed regulation #)", "https://www.arcgis.com/home/item.html?id=45a20b2d367d47bb85d5a70ca81e2cd0"),
 "FHWA": ("https://geo.dot.gov/server/rest/services/Hosted/FHWA__2022_Speed_Limit_Study_Results__All_States/FeatureServer/0", "speed_limit", "route_id", "FHWA 2022 speed limit study (HPMS 2020, NHS roads)", "https://geo.dot.gov/server/rest/services/Hosted/FHWA__2022_Speed_Limit_Study_Results__All_States/FeatureServer/0"),
}
regs = {r["id"]: r for r in json.load(open(os.path.join(ROOT, "public/data/regions.json")))}
for rid in sys.argv[1:]:
    r = regs[rid]; S, W, N, E = r["bbox"]; out = []
    for key in ([r["state"]] if r["state"] in SRC else []) + ["FHWA"]:
        u, f, nm, lab, link = SRC[key]; off = 0
        while True:
            q = {"f": "geojson", "where": "1=1", "outFields": f"{f},{nm}", "returnGeometry": "true", "outSR": 4326, "inSR": 4326, "geometry": f"{W},{S},{E},{N}", "geometryType": "esriGeometryEnvelope", "spatialRel": "esriSpatialRelIntersects", "resultOffset": off, "resultRecordCount": 1000}
            for a in range(3):
                try: d = json.load(urllib.request.urlopen(u + "/query?" + urllib.parse.urlencode(q), timeout=90)); break
                except Exception as e: print("retry", rid, key, e); time.sleep(3); d = {"features": []}
            fs = d.get("features", [])
            for ft in fs:
                g = ft.get("geometry") or {}; v = (ft.get("properties") or {}).get(f)
                if not v: continue
                parts = g.get("coordinates", []) if g.get("type") == "MultiLineString" else [g.get("coordinates", [])]
                for pt in parts:
                    if len(pt) > 1: out.append({"mph": int(v), "label": f"{lab}: {ft['properties'].get(nm)} posted {int(v)} mph", "url": link, "src": key, "coords": pt})
            off += len(fs)
            if not fs or not d.get("properties", {}).get("exceededTransferLimit"): break
    json.dump(out, open(os.path.join(ROOT, "cache", rid + "_dot.json"), "w"))
    print(rid, len(out), "dot lines", {k: sum(1 for o in out if o["src"] == k) for k in set(o["src"] for o in out)})
