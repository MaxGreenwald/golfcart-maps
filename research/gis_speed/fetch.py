#!/usr/bin/env python3
"""Download public speed-limit GIS layers clipped to region bboxes (GeoJSON, WGS84) into raw/. Analysis only."""
import json, os, sys, urllib.request, urllib.parse
SRC = {  # name: (layer url, region, where)
 "fdot_naples": ("https://services1.arcgis.com/O1JpcwDW8sjYuddV/arcgis/rest/services/Maximum_Speed_Limit_TDA/FeatureServer/0", "naples", "1=1"),
 "fdot_villages": ("https://services1.arcgis.com/O1JpcwDW8sjYuddV/arcgis/rest/services/Maximum_Speed_Limit_TDA/FeatureServer/0", "villages", "1=1"),
 "fl_cts_collier": ("https://gis.ctsfl.us/arcgis/rest/services/Hosted/SpeedLimit/FeatureServer/0", "naples", "1=1"),
 "fl_cts_villages": ("https://gis.ctsfl.us/arcgis/rest/services/Hosted/SpeedLimit/FeatureServer/0", "villages", "1=1"),
 "sumter_roads": ("https://gisweb.sumtercountyfl.gov/sumtergis/rest/services/Public/Cityworks_Active/FeatureServer/58", "villages", "1=1"),
 "scdot_speed": ("https://gis.scdot.org/hosting/rest/services/Speed_Limits/FeatureServer/16", "myrtle", "1=1"),
 "rivco_highways": ("https://gis.countyofriverside.us/arcgis_mapping/rest/services/OpenData/Transportation/MapServer/1", "coachella", "1=1"),
 "ocgis_speed": ("https://ocgis.com/arcpub/rest/services/OC_Infrastructure/Traffic_Investigations/FeatureServer/0", "ocoast", "1=1"),
}
BB = {"villages": [28.78, -82.1, 29.02, -81.9], "myrtle": [33.55, -79.1, 33.92, -78.65], "suncity": [33.57, -112.4, 33.72, -112.22],
      "coachella": [33.62, -116.45, 33.83, -116.18], "naples": [25.9, -81.82, 26.3, -81.68], "ocoast": [33.38, -117.8, 33.65, -117.58]}
os.makedirs("raw", exist_ok=True)
for name in (sys.argv[1:] or SRC):
    url, r, where = SRC[name]; s, w, n, e = BB[r]; feats = []; off = 0
    while True:
        q = dict(where=where, geometry=f"{w},{s},{e},{n}", geometryType="esriGeometryEnvelope", inSR=4326, outSR=4326,
                 spatialRel="esriSpatialRelIntersects", outFields="*", f="geojson", resultOffset=off, resultRecordCount=1000)
        d = json.load(urllib.request.urlopen(urllib.request.Request(url + "/query?" + urllib.parse.urlencode(q), headers={"User-Agent": "Mozilla/5.0"}), timeout=120))
        fs = d.get("features", []); feats += fs; off += len(fs)
        if not fs or not (d.get("exceededTransferLimit") or d.get("properties", {}).get("exceededTransferLimit")): break
    json.dump({"type": "FeatureCollection", "source": url, "features": feats}, open(f"raw/{name}.geojson", "w"))
    print(name, len(feats))
