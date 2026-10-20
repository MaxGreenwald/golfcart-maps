# Street View batch 1 results (ingested 2026-10-19)

Source: volunteer sheet 1g5lYzIc_Roj82UB1I5LiG0ia-wv9T9ltDAP56jjXmKw, tab Roads (export saved as streetview.csv; analyze.py reads it).
100 rows: 24 done (sign read), 76 "can't tell" (no readable sign in the segment), 0 pending.
analyze.py rerun: verified ways unchanged at 66 (the strict any-disagreement rule keeps the 7 Carlsbad Blvd 50 mph ways as
"disagree" because OSM still says 30, though official 50 + the sign photo 50 agree). 1 way moved one unofficial -> OSM + imagery.

Sign vs map (current master data):
- La Jolla Blvd Carla Way-Colima (4 ways, sign 35) and Mission Blvd Diamond-Missouri (sign 30): already 35/30 on master
  (sd-safety-caution rule). The sheet's "our 25" was the older snapshot. Confirms that fix.
- South Coast Hwy, Solana Beach, Estrella-Lomas Santa Fe: map 30, sign 35. No legality change (LSV ok, cart not either way). Engineer to update.
- Carlsbad Blvd S Coast Hwy-Mountain View (map/official 35, sign 25 ~300 m away) and S Vulcan Ave, Encinitas (map/official 30,
  sign 25 ~300 m away): map is stricter. Not loosened on one sign that is outside the segment; city confirmation needed.
- Proposal for Max/Manager: treat official + dated sign photo agreeing as verified even when OSM disagrees (would verify 7 Carlsbad Blvd ways).
