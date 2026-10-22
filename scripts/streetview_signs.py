"""Posted speed signs read by a person in Google Street View (batch 2, RG, Oct 2026): research/streetview_batch2/signs.json.
A posted sign is a real source, so it overrides OSM tags, guesses from road type and Mapillary detections. It never lifts a
ban (ordinance/state-highway bans stay), and when an official source already sets a different limit on the way the two real
sources conflict: the official one stays and the conflict is listed (Max's rule, Oct 20: conflicting real sources stay unresolved).
Each entry cites 'posted sign, Street View check (RG), photo <file>' and links the photo."""
import json, os
_P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "research", "streetview_batch2", "signs.json")
ALL = json.load(open(_P)) if os.path.exists(_P) else {}
def for_region(rid): return {e["way"]: e for e in ALL.get(rid, [])}
