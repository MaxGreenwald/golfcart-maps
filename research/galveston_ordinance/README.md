# Galveston, TX golf cart / NEV ordinance scrub (Nov 24 2026)

Trigger: Mark Searcy (Mark's Karts, Galveston rental shop) said on a call with Max that the map was far too
restrictive. Every change below is backed by an official City of Galveston text. Mark's notes were used only to
pick which streets to check.

## Sources (text extracts in this folder, PDF hashes in pdf_sha256.txt)

| File | Source |
|---|---|
| ord_21-023_golf_carts.txt | Ord. 21-023 (June 24 2021), Chapter 34 Art. IX, https://www.galvestontx.gov/DocumentCenter/View/12508/Golf-Cart-Ordinance-June-2021 |
| ch34_speed_sections.txt | Code Chapter 34 Sec. 34-56 to 34-59 (speed schedule), https://galvestontx.gov/DocumentCenter/View/11414/Chapter_34___TRAFFIC (PDF dated Oct 29 2020) |
| ord_17-050_seawall_35.txt | Ord. 17-050 (July 27 2017): Seawall Blvd 35 mph from Ferry Rd to 61st St |
| engineering_memo_2025-01-23.txt | City engineering memo, Jan 23 2025: streets with no listed zone default to Tex. Transp. Code 545.352, 30 mph |

Em dashes in the city text are shown as hyphens.

## Ordinance rules (Sec. 34-203(b) as amended by Ord. 21-023)

Golf carts and NEVs (the ordinance counts NEVs as golf carts) may not use:
1. streets posted over 35 mph;
2. Avenue O between 53rd and 15th Streets, and Avenue P between 19th and 53rd Streets (east of 25th St OSM names
   Avenue P "Bernardo De Galvez Avenue", alt_name Avenue P);
3. the Pelican Island Causeway;
4. state-highway streets, including: SH 275 Harborside Dr (IH 45 to Ferry Rd); Spur 342 61st St (IH 45 to Seawall);
   SH 87 Broadway (59th to 6th), Seawall Blvd (6th St to Ferry Rd) and Ferry Rd (Seawall to Ferry Landing);
   FM 3005 Seawall Blvd west of 61st St and San Luis Pass Rd to the toll bridge; FM 188 Teichman Rd; IH 45;
   Park Road at the State Park; SH 168 Fort Point Rd.
Sec. 34-207(d) (renumbered 34-209): a cart on a permitted street may cross an excluded street.
Other rules not modeled: dual permit east/west of 103rd St (east-of-103rd carts need turn signals, horn, brake lights,
seat belts); right-hand lane only on multi-lane streets; no sidewalks; plates and city permit required.

## Speed schedule used (Code Sec. 34-56, 34-58, 34-59)

Sec. 34-56: state speed law applies on every street except the listed zones. Unlisted streets in town therefore carry
the Tex. Transp. Code 545.352(b)(1) urban default of 30 mph (the Jan 2025 memo says the same).
Listed zones used here: Seawall Blvd Ferry Rd to 61st St 35 (34-58(a)(3)); Stewart Rd 61st to 85th St 35
(34-58(a)(6)); Jones Dr 69th St to Stewart Rd 35 (34-58(a)(7)); 61st St 40 (34-58(b)(1)); Seawolf Pkwy from
Bradner 45 (34-59(b)(2)); Bradner St 45 (34-59(b)(3)); Seawall east of Ferry Rd 45 (34-59(b)(4)); Stewart Rd 85th St to
west city limit 45 (34-59(b)(5)); Apffel Park Rd Seawall to Lakeside Dr 30 and Lakeside Dr to the park 40 (34-59(g)(1), (h)(1)); 9 Mile and 10 Mile Rd Homrighaus to Stewart 45 (34-59(b)(9), (10)).

## What changed (research/regions/galveston.json, rebuilt with scripts/build_region.py galveston)

See diff_summary.txt for per-road miles. Opened (now legal): Seawall Blvd 6th St to 61st St; 6th St / University
Blvd; 14th, 21st (Moody), 29th (MLK), 37th, 39th (Mike Gaido, red-island check), 53rd (Mary Moody Northern), 81st
(Jones Dr to Stewart Rd) Streets; Market St; Stewart Rd 61st St area; Jones Dr; the Avenue O block west of 53rd St.
Closed (safety): Park Road 66; Avenue P / Bernardo De Galvez Ave 25th to 19th St; SH 87 ramp at Seawall/Ferry;
the SH 275 piece of 6th St at Harborside Dr; Seawolf Pkwy east of Bradner; Bradner Rd; 9 Mile and 10 Mile Rd
north of Stewart Rd; Apffel Park Rd from Lake Side Dr to the park (40 mph, 34-59(h)(1)).

## Left as is (listed for Max)

- Stewart Rd west of 85th St and 8 Mile Rd: Code 34-59(b) lists 45 mph, but posted signs read in Street View or
  Mapillary show 35 / 30. Kept the posted-sign value; needs a check.
- Every other unknown-speed (99i) city street: the same 30 mph default would apply region-wide. Not done (region
  default needs Max's OK).
