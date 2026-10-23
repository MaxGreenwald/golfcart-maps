#!/usr/bin/env python3
"""Writes research/regions/southbay.json: hand-written bans/notes below + speed_names from speed_table.py."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, HERE)
import speed_table
CVC21260 = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum=21260."
CVC21716 = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum=21716."
SHC1953 = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=SHC&sectionNum=1953."
MB1428 = "https://gocodebook.com/library/us/ca/manhattan-beach/title-14-traffic/chapter-14.28-miscellaneous-driving-rules"
HB1220 = "https://online.encodeplus.com/regs/hermosabeach-ca/doc-view.aspx?secid=1685"
HB1012 = "https://online.encodeplus.com/regs/hermosabeach-ca/doc-view.aspx?secid=3103"
sn, bad = speed_table.main()
for x in bad: print("UNRESOLVED", x)
sn.append({"names": ".", "mph": 25, "poly": "hermosa_beach.json", "highway": "^(secondary|tertiary|unclassified|residential|living_street)$",
           "url": speed_table.SRC["HB"][0], "label": "Hermosa Beach Municipal Code 10.40.020: every Hermosa Beach street not listed is 25 mph"})
# Unnamed PCH slip lane at Palos Verdes Blvd (Redondo/Torrance line): FHWA says 60, but both city codes post PCH 35 here.
sn.append({"names": "^$", "mph": 35, "highway": "^primary_link$", "bboxes": [[33.8186, -118.3846, 33.8192, -118.3840]],
           "url": speed_table.SRC["RB"][0], "label": "Redondo Beach Municipal Code 3-7.503: Pacific Coast Highway, Palos Verdes Boulevard to 190th Street, 35 mph (slip lane at Palos Verdes Blvd)"})
cfg = {
 "poly": json.load(open("/tmp/sb_poly.json")) if os.path.exists("/tmp/sb_poly.json") else json.load(open(os.path.join(ROOT, "research/regions/southbay.json")))["poly"],
 "private_polys": ["rolling_hills.json"], "private_keep": "^Palos Verdes Drive North$",
 "unverified": [
  "Rolling Hills is a gated private city: its roads are private and are not drawn. You need the residents' gate access to drive there.",
  "The Strand, the beach bike path, the piers, Pier Plaza and Manhattan Beach's walk streets are closed to all motor vehicles (MBMC 14.28, HBMC 12.20.220). They are pedestrian ways in OpenStreetMap, so they are not drawn.",
  "Posted limits come from each city's speed-zone ordinance, matched to OpenStreetMap by cross streets. Short stretches at zone ends can be off by a block; the higher limit is shown where two zones meet.",
  "Rancho Palos Verdes and Rolling Hills Estates don't list speeds in their codes. RPV limits come from the city's 2018 General Plan traffic study. Palos Verdes Drive East (30 to 40 mph, 35 on the switchbacks since 2025), Silver Spur Road (35 to 45) and Palos Verdes Drive North in Rolling Hills Estates use OpenStreetMap or sign data. Check the signs.",
  "Pacific Coast Highway and Sepulveda Boulevard (SR-1) and Western Avenue (SR-213) are state highways: no golf carts. LSVs only where posted 35 or less.",
  "The South Bay Local Travel Network (AB 2432) signs some 25-35 mph streets for low-speed vehicles. It is shown as a resource, not as a separate layer.",
  "Local residential streets with no posted limit in OpenStreetMap are assumed 25 mph (California residence district) and shown green, not verified. Hermosa Beach's code makes every unlisted street 25."
 ],
 "bans": [
  {"names": "^I[ -]?(405|105|110)\\b|^CA[ -]?91\\b|Freeway$", "url": CVC21260, "label": "Freeways (I-405, I-105, I-110, SR-91): 65 mph; LSVs only on roads posted 35 or less (CVC 21260), golf carts 25 or less (CVC 21716)"},
  {"names": "^(The )?Strand$", "bbox": [33.855, -118.43, 33.905, -118.39], "url": MB1428, "label": "Manhattan Beach Strand and walk streets: no vehicles (MBMC 14.28.120 beach, 14.28.130 bike path, 14.28.150 walk streets)"},
  {"names": "^(The )?Strand$|Pier Plaza", "bbox": [33.84, -118.43, 33.875, -118.39], "url": HB1220, "label": "Hermosa Beach Strand walkway, Pier Plaza and beach: no motorized vehicles (HBMC 12.20.220)"},
  {"names": "Greenbelt", "bbox": [33.84, -118.42, 33.89, -118.39], "url": HB1012, "label": "Hermosa Valley Greenbelt: no motorized conveyances (HBMC 10.12.175)"},
  {"names": "Pier$", "bbox": [33.82, -118.43, 33.89, -118.38], "url": MB1428, "label": "Piers: no vehicles (MBMC 14.28.110; HBMC 12.20.220)"}
 ],
 "cart_only_bans": [
  {"names": "^CA ?1$|Pacific Coast Highway$", "url": SHC1953, "label": "SR-1 (Pacific Coast Highway / Sepulveda Blvd) is a state highway: golf carts only on local streets posted 25 or less (CVC 21716); a golf cart plan can't use a state highway without Caltrans approval (S&H Code 1953)"},
  {"names": "^CA ?213$", "url": SHC1953, "label": "SR-213 (Western Ave) is a state highway: no golf carts (CVC 21716; S&H Code 1953)"}
 ],
 "speed_names": sn,
 "sources": [
  "CVC 21260 (LSVs: roads posted 35 mph or less) " + CVC21260,
  "CVC 21716 (golf carts: 25 mph or less) " + CVC21716,
  "CVC 21115 / 21115.1 (local golf cart rules) https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum=21115.",
  "Streets & Highways Code 1950-1965 golf cart transportation plans " + SHC1953,
  "Manhattan Beach Municipal Code ch. 14.28 (Strand, pier, beach, walk streets) " + MB1428,
  "Manhattan Beach Municipal Code 3.01.040 (no e-bikes on the Strand) https://gocodebook.com/library/us/ca/manhattan-beach/title-3-public-safety/chapter-3.01-bicycles-1",
  "Hermosa Beach Municipal Code 12.20.220 (Strand, Pier Plaza, beach) " + HB1220,
  "Hermosa Beach Municipal Code 10.12.175 (Greenbelt) " + HB1012,
  "Redondo Beach Municipal Code 4-35.06 (no motor vehicles in parks) https://ecode360.com/42651406",
 ] + ["%s %s" % (v[1], v[0]) for v in speed_table.SRC.values()] + [
  "Rolling Hills Estates Municipal Code ch. 10.28 (Silver Spur, PV Drive North weight limits) https://gocodebook.com/library/us/ca/rolling-hills-estates/title-10-vehicles-and-traffic/chapter-10.28-use-restrictions-for-specific-streets",
  "South Bay Cities COG, South Bay Local Travel Network (AB 2432) https://southbaycities.org/media-center/south-bay-local-travel-network-media-kit/",
  "AB 2432 (2022) LA County NEV plans https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202120220AB2432",
  "Rancho Palos Verdes AB 2432 staff report https://rpv.granicus.com/MetaViewer.php?event_id=2076&meta_id=103430&view_id=5",
 ],
 "enforcement": {"checked": "2026-10-22", "result": "bans_applied", "sources": [
   {"label": "Manhattan Beach MBMC 14.28 (no vehicles on the Strand, pier, beach or walk streets)", "url": MB1428},
   {"label": "Hermosa Beach HBMC 12.20.220 (no motorized vehicles on the Strand walkway, Pier Plaza or beach)", "url": HB1220},
   {"label": "CVC 21260 (LSVs only on roads posted 35 mph or less)", "url": CVC21260},
   {"label": "CVC 21716 (golf carts only where posted 25 mph or less)", "url": CVC21716}],
  "note": "No South Bay city has adopted a golf cart transportation plan that we found; golf carts follow CVC 21716 (25 mph or less). The Strand and walk streets are enforced by MBPD/HBPD."},
 "status": "region-southbay preview (2026-10-22)"
}
json.dump(cfg, open(os.path.join(ROOT, "research/regions/southbay.json"), "w"), indent=1)
print("speed_names", len(sn))
