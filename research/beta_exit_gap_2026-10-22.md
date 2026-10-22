# Beta-exit gap, 2026-10-22

Bar (Max): a region leaves beta when **70% of its important roads** are backed by a real source.

- Important roads: primary, secondary, tertiary and their `_link`s, plus trunk only when posted <= 35 mph (fast trunk excluded).
- Real source: code `v` (manual fix / ban / DOT), `m` (Mapillary sign), or `d` only when the segment links a source. Not counted: `t i n q r k`.
- Segments are deduped by node pair across tiles. Miles are geometric length. Data: built `public/data/` on branch `streetview-batch2-apply` (includes batch 2).
- "Segs to 70%" = extra sourced segments needed (segment basis). Batches assume 1,000 segments per batch, rounded up per region.
- Reproduce: `python3 research/beta_exit_gap.py 35`

| Region | Important segs | Sourced | % segs | Important mi | Sourced mi | % miles | Segs to 70% | Batches (1,000) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| oob | 568 | 548 | 96.5% | 30.7 | 29.8 | 97.3% | 0 | 0 |
| annamaria | 324 | 307 | 94.8% | 15.3 | 14.8 | 97.0% | 0 | 0 |
| tybee | 179 | 154 | 86.0% | 8.7 | 7.7 | 88.5% | 0 | 0 |
| amelia | 791 | 680 | 86.0% | 51.7 | 47.7 | 92.3% | 0 | 0 |
| southpadre | 557 | 474 | 85.1% | 25.6 | 21.9 | 85.4% | 0 | 0 |
| staug | 1,861 | 1,571 | 84.4% | 131.0 | 111.5 | 85.1% | 0 | 0 |
| gulfshores | 1,037 | 846 | 81.6% | 89.4 | 64.2 | 71.8% | 0 | 0 |
| 30a | 808 | 581 | 71.9% | 55.1 | 38.8 | 70.4% | 0 | 0 |
| pcb | 1,676 | 1,139 | 68.0% | 74.3 | 48.6 | 65.4% | 35 | 1 |
| rockport | 562 | 371 | 66.0% | 56.3 | 39.7 | 70.5% | 23 | 1 |
| siesta | 5,801 | 3,826 | 66.0% | 300.0 | 213.6 | 71.2% | 235 | 1 |
| obx | 885 | 583 | 65.9% | 72.2 | 47.2 | 65.4% | 37 | 1 |
| chs | 855 | 556 | 65.0% | 57.1 | 40.2 | 70.4% | 43 | 1 |
| keywest | 791 | 480 | 60.7% | 34.9 | 21.8 | 62.4% | 74 | 1 |
| kailua | 590 | 348 | 59.0% | 40.2 | 29.0 | 72.0% | 65 | 1 |
| portaransas | 586 | 340 | 58.0% | 39.6 | 29.7 | 75.0% | 71 | 1 |
| destin | 910 | 526 | 57.8% | 45.7 | 23.6 | 51.8% | 111 | 1 |
| galveston | 2,911 | 1,613 | 55.4% | 172.5 | 109.2 | 63.3% | 425 | 1 |
| lwr | 1,376 | 759 | 55.2% | 158.4 | 102.7 | 64.8% | 205 | 1 |
| poipu | 141 | 75 | 53.2% | 18.4 | 12.6 | 68.9% | 24 | 1 |
| bhi | 463 | 237 | 51.2% | 44.4 | 17.0 | 38.3% | 88 | 1 |
| suncitycenter | 665 | 332 | 49.9% | 57.0 | 32.2 | 56.6% | 134 | 1 |
| kaanapali | 211 | 105 | 49.8% | 23.9 | 14.0 | 58.6% | 43 | 1 |
| myrtle | 8,379 | 3,939 | 47.0% | 525.6 | 233.7 | 44.5% | 1,927 | 2 |
| wailea | 571 | 266 | 46.6% | 36.2 | 22.0 | 60.8% | 134 | 1 |
| naples | 6,767 | 3,060 | 45.2% | 465.9 | 227.5 | 48.8% | 1,677 | 2 |
| hhi | 1,202 | 527 | 43.8% | 95.7 | 35.6 | 37.2% | 315 | 1 |
| ptc | 1,746 | 646 | 37.0% | 163.0 | 51.2 | 31.4% | 577 | 1 |
| goldenisles | 675 | 243 | 36.0% | 64.8 | 27.4 | 42.3% | 230 | 1 |
| waikoloa | 275 | 96 | 34.9% | 48.1 | 19.2 | 39.9% | 97 | 1 |
| sd | 31,671 | 9,813 | 31.0% | 1,455.9 | 489.0 | 33.6% | 12,357 | 13 |
| avalon | 54 | 13 | 24.1% | 6.2 | 2.3 | 36.2% | 25 | 1 |
| suncity | 7,996 | 1,577 | 19.7% | 458.5 | 119.3 | 26.0% | 4,021 | 5 |
| ocoast | 13,561 | 2,455 | 18.1% | 704.9 | 179.7 | 25.5% | 7,038 | 8 |
| coachella | 6,681 | 1,101 | 16.5% | 521.2 | 92.5 | 17.8% | 3,576 | 4 |
| villages | 4,720 | 706 | 15.0% | 384.9 | 75.1 | 19.5% | 2,598 | 3 |
| putinbay | 81 | 0 | 0.0% | 7.9 | 0.0 | 0.0% | 57 | 1 |
| **All 37** | 108,927 | 40,893 | 37.5% | 6,541 | 2,692 | 41.2% | 36,242 | 59 |

Passing (>=70% by segments): 8/37

## Notes
- 8 of 37 pass today. 14 more need under 250 segments each (one small batch).
- SD, Orange County coast, Sun City, Coachella, The Villages, Myrtle and Naples hold 33,194 of the 36,242 segments still needed (~92%). Those need bulk sources (city/county GIS, state DOT speed data, wider Mapillary, the Sumter County list), not hand checks.
- Earlier partial figures (SD 33.2%, Villages 16.2%, 30A 80.6%) used a different counting method; this table replaces them.
