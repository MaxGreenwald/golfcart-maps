# Public speed-limit GIS layers for the big regions (2026-10-22, analysis only, nothing imported)

- `fetch.py` downloads each layer, clipped to the region bbox, into `raw/` (gitignored).
- `match.py` test-matches each layer to our important-road segments. A segment matches when its 25%, 50% and 75% points all fall within 20 m of the same GIS line.
- **Agree** = the GIS speed equals our real-source speed (`v`/`m`).
- **Gap mi** = unsourced important miles the layer would cover.
- **More permissive** = covered segments where the GIS says <=35 but we show >35. These need a review before any import.

| Region | Layer (URL) | Format | License / terms | Has speeds? | Features in bbox | Agree with our sources | Gap mi covered | % sourced if imported | More permissive |
|---|---|---|---|---|---:|---:|---:|---|---:|
| Naples | FDOT Maximum Speed Limit TDA, https://services1.arcgis.com/O1JpcwDW8sjYuddV/arcgis/rest/services/Maximum_Speed_Limit_TDA/FeatureServer/0 (also weekly shapefile at https://www.fdot.gov/statistics/gis/default.shtm) | ArcGIS FeatureServer / GeoJSON / shapefile | FDOT public data, "as is", no warranty | yes, `SPEED` (state roads only) | 91 | 98% (876/896) | 20.2 | 48.8% -> 53.2% | 13 |
| The Villages | same FDOT layer | same | same | yes (state roads only) | 189 | 89% (42/47) | 101.5 | 19.5% -> 45.9% | 50 |
| The Villages | Sumter County Roads (Cityworks), https://gisweb.sumtercountyfl.gov/sumtergis/rest/services/Public/Cityworks_Active/FeatureServer/58 | FeatureServer | public county GIS, no license stated | `SpeedLimit` field, but values look like defaults (20/30/5) | 11,564 | **0% (0/37)** | 166 | (not usable) | 57 |
| Myrtle Beach | SCDOT Speed Limits, https://gis.scdot.org/hosting/rest/services/Speed_Limits/FeatureServer/16 (+ "Speed Limits Highways" shapefile on info2.scdot.org) | FeatureServer / shapefile | SCDOT public data, no license stated | yes, `Regulatory` (state routes only) | 193 | 95% (1,399/1,476) | 4.2 | 44.5% -> 45.3% | 17 |
| Orange County coast | OC Public Works Traffic Investigations "Speed Limits", https://ocgis.com/arcpub/rest/services/OC_Infrastructure/Traffic_Investigations/FeatureServer/0 | FeatureServer | county public GIS, no license stated | yes, `Speed_Limit` + `Survey_Date` (unincorporated OC only: Ladera, Rancho Mission Viejo, Coto) | 26 | 89% (88/99) | 16.3 | 25.5% -> 27.8% | 64 |
| Orange County coast | City of Irvine Speed, https://gis.cityofirvine.org/arcgis/rest/services/ADT/MapServer/11 | MapServer | city GIS | yes | not in ocoast bbox | - | - | - | - |
| Coachella | Riverside County Highways, https://gis.countyofriverside.us/arcgis_mapping/rest/services/OpenData/Transportation/MapServer/1 | MapServer | county open data | `SPEED` on state highways only | 79 | n=2 | 0.2 | no change | 0 |
| Coachella | City of Indio speed zones: Resolution 10467 (129 segments, PDF + map), https://indio.civicweb.net/document/177043 | PDF | public record | yes (PDF, would need digitizing) | - | - | - | - | - |
| Sun City AZ | Maricopa County GIS Open Data, https://data-maricopa.opendata.arcgis.com/ | Hub | **internal use only; external or commercial use needs written GIS-office authorization** | no public speed layer found (the MCDOT Road Information Tool has none) | - | - | - | - | - |
| all CA | Caltrans: no statewide posted-speed layer. FHWA 2022 HPMS speed study (NHS roads only), https://geo.dot.gov/server/rest/services/Hosted/FHWA__2022_Speed_Limit_Study_Results__All_States/FeatureServer | FeatureServer | federal, public domain | NHS only | not tested | | | | |
| FL (Pasco/Pinellas) | CTS "FDOT and County Roadway Speed Limits", https://gis.ctsfl.us/arcgis/rest/services/Hosted/SpeedLimit/FeatureServer/0 | FeatureServer | - | yes, but only Pasco and Pinellas counties | 0 | - | - | - | - |

**Read:**
- Usable now:
  - FDOT for Naples (98%). Much of it is already applied as `v` through `cache/*_dot.json`.
  - SCDOT for Myrtle Beach (95%).
- Usable with review:
  - FDOT for The Villages and the OC county layer, both 89%.
  - Every "more permissive" row must be checked first, since it would turn red roads green.
- Not usable:
  - The Sumter County `SpeedLimit` field: 0% agreement, looks like placeholders.
  - Maricopa County: its license blocks use without written permission.
  - Coachella: no city or county GIS speed layer was found. The Indio resolution PDF is the best lead; Palm Desert and La Quinta publish no layer.
  - Remaining OC cities (Mission Viejo, Laguna Niguel, San Clemente, Dana Point) publish PDF maps or speed surveys, not GIS.
