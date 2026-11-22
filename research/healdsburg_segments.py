"""Healdsburg Municipal Code 10.50.050 (https://ecode360.com/47365641), one row per code segment.
(street regex, mph, code segment text, box [S, W, N, E] or None). Boxes come from OpenStreetMap
intersection nodes. Every row is also limited to the city limits (research/city_limits/healdsburg.json).
The Memorial Bridge (15 mph, 10.50.060) is folded into its 30 mph east approach, the stricter of the two.
North Street (20 mph, Grove/Vine Street to East Street) is left out: OpenStreetMap draws it as one way that runs
past East Street, so it keeps the 25 mph default. Both speeds are under both caps.
Kinley Drive (35 mph, Westside Road to Magnolia Drive South) is outside the OpenStreetMap city line, so it is not drawn."""
HA = r"^Healdsburg Avenue$"
SEGMENTS = [
    (HA, 35, "Healdsburg Avenue, northern city limits to Parkland Farms Boulevard", [38.6379, -122.880, 38.700, -122.860]),
    (HA, 30, "Healdsburg Avenue, Parkland Farms Boulevard to Powell Avenue", [38.6207, -122.880, 38.6379, -122.860]),
    (HA, 25, "Healdsburg Avenue, Powell Avenue to Piper Street", [38.6143, -122.880, 38.6207, -122.860]),
    (HA, 20, "Healdsburg Avenue, Piper Street to Mill Street", [38.6084, -122.880, 38.6143, -122.860]),
    (HA, 25, "Healdsburg Avenue, Mill Street to Front Street/Kennedy Lane", [38.6036, -122.880, 38.6084, -122.8611]),
    (HA, 30, "Healdsburg Avenue, Memorial Bridge and its east approach to Bailhache Avenue", [38.6031, -122.8611, 38.6045, -122.850]),
    (HA, 35, "Healdsburg Avenue, Bailhache Avenue to southern city limits", [38.550, -122.870, 38.6031, -122.840]),
    (r"^Center Street$", 25, "Center Street, Powell Avenue to North Street", [38.6122, -122.875, 38.6215, -122.865]),
    (r"^Center Street$", 20, "Center Street, North Street to Mill Street", [38.6080, -122.875, 38.6122, -122.865]),
    (r"^Chiquita Road$", 30, "Chiquita Road, city limits north to Grove Street", None),
    (r"^Dry Creek Road$", 25, "Dry Creek Road, US 101 to Healdsburg Avenue", [38.620, -122.8792, 38.630, -122.870]),
    (r"^(Fitch|Harmon|Hudson) Street$", 25, "Fitch, Harmon and Hudson Streets", None),
    (r"^Front Street$", 25, "Front Street, Mason Street to Healdsburg Avenue", [38.6035, -122.870, 38.6080, -122.855]),
    (r"^(West )?Grant (Street|Avenue)$", 25, "Grant Avenue, Grove Street to University Street", [38.614, -122.8760, 38.618, -122.8630]),
    (r"^(Grove|Vine) Street$", 25, "Grove Street and Grove/Vine Street, Healdsburg Avenue to Mill Street", None),
    (r"^March Avenue$", 25, "March Avenue, Healdsburg Avenue to Woodside Court", None),
    (r"^(West )?Matheson Street$", 20, "Matheson Street, western city boundary to East Street", [38.600, -122.900, 38.620, -122.8683]),
    (r"^Matheson Street$", 25, "Matheson Street, East Street to Heron Street", [38.600, -122.8683, 38.620, -122.850]),
    (r"^Mill Street$", 25, "Mill Street, East Street to US 101", None),
    (r"^Parkland Farms Boulevard$", 35, "Parkland Farms Boulevard, Healdsburg Avenue to Saddle Draw", None),
    (r"^Plaza Street$", 20, "Plaza Street, Healdsburg Avenue to Center Street", None),
    (r"^Powell Avenue$", 25, "Powell Avenue, Healdsburg Avenue to eastern city limits", None),
    (r"^South Fitch Mountain Road$", 30, "South Fitch Mountain Road, Heron Drive to eastern city limits", [38.600, -122.857, 38.630, -122.830]),
    (r"^Terrace Boulevard$", 25, "Terrace Boulevard, Healdsburg Avenue to University Street", None),
    (r"^University Avenue$", 30, "University Avenue, Terrace Boulevard to Powell Avenue", None),
    (r"^University Street$", 25, "University Street, Powell Avenue to Mason Street", [38.600, -122.870, 38.6207, -122.860]),
]
