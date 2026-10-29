"""Posted speed signs read by a person in Google Street View (RG, Oct 2026): research/streetview_batch2/signs.json and
research/streetview_batch4/signs.json. A posted sign is a real source, so it overrides OSM tags, guesses from road type
and Mapillary detections. It never lifts a ban (ordinance/state-highway bans stay), and when an official source already sets
a different limit on the way the two real sources conflict: the official one stays and the conflict is listed (Max's rule,
Oct 20: conflicting real sources stay unresolved). Each entry cites 'posted sign, Street View check (RG), photo <file>' and
links the photo. Two batches never claim the same way with different limits (checked here and in tests)."""
import json, os
_R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "research")
BATCHES = ("streetview_batch2", "streetview_batch4")
ALL = {}
for _b in BATCHES:
    _P = os.path.join(_R, _b, "signs.json")
    if not os.path.exists(_P): continue
    for _rid, _v in json.load(open(_P)).items(): ALL.setdefault(_rid, []).extend(_v)
def for_region(rid):
    out = {}
    for e in ALL.get(rid, []):
        if e["way"] in out and out[e["way"]]["mph"] != e["mph"]:
            raise ValueError(f"Street View batches disagree on way {e['way']} ({rid}): {out[e['way']]['check_id']} vs {e['check_id']}")
        out.setdefault(e["way"], e)
    return out
