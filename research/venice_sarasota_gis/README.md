# Sarasota County Street GIS extract (Venice, FL)

Official written source for the Venice posted-speed fix (north Pinebrook Road at 40 mph, and the LSV-open eastern mainline of Laurel Road East at 40 or 45 mph).

- Layer: [Sarasota County Street GIS](https://ags3.scgov.net/server/rest/services/Hosted/Street/FeatureServer/0)
- Field: `speedlimit`
- Queried: 2026-11-23
- Records: see `speedlimit_extract.json` (OBJECTID, Street ID, speed, maintenance entity, last update in PT)

Tracy Self, Office Manager, City of Venice Public Works, replied on 2026-11-23 that these are Sarasota County roads and that the speed limit should be posted. She did not give a miles-per-hour figure. The speeds in this extract come from the county Street layer, not from that email.

This extract is the cited source for `research/regions/venice.json` `speed_names`. It is not a license to change Center Road, Albee Farm Road, the already-closed Laurel Road East segments, or Pinebrook Road south of Edmondson Road.
