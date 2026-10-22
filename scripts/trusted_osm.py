"""Trusted OpenStreetMap limits, source code 'o' (Max approved 2026-10-22).
An OSM-tagged segment (code 't') becomes 'o' when ALL hold:
  - its maxspeed is a real number (not an implied/default value like US:urban, not from a vehicle code/default source),
  - it is not banned, and
  - an adjacent segment of the same road (shares a node, same name) is backed by a real source (v, m, or d with a
    source link), is not banned, and posts the SAME mph.
Measured agreement of this rule with real sources: 98.5% (n=6,782; research/beta_exit_gap_v2_2026-10-22.md).
Relabel only: the speed is never changed, so 'o' can never lift a ban or turn a road green. Run after every speed pass."""
import re
IMPLIED = re.compile(r"^[a-z]{2}(-[a-z]{2})?:|vehicle code|motor vehicle|default|implied|zone", re.I)

def explicit(t):
    """True when the way's maxspeed is a plain posted number and nothing says it is an implied/default value."""
    ms = (t.get("maxspeed") or "").strip()
    if not re.match(r"^\d+(\s*mph)?$", ms): return False
    return not any(IMPLIED.search(t.get(k) or "") for k in ("source:maxspeed", "maxspeed:type", "zone:maxspeed", "source:maxspeed:type"))

def _real(s): return s[3] in ("v", "m") or (s[3] == "d" and len(s) > 8 and s[8] >= 0)
def _banned(s): return len(s) > 9 and s[9] == 1

def mark(out, expl):
    """out: built segments [name, hw, mph, code, oneway, a, b, pts, (src, flag)]; expl: indices whose OSM tag is explicit.
    Returns the number of segments relabelled 't' -> 'o'."""
    at = {}
    for i, s in enumerate(out):
        for n in (s[5], s[6]): at.setdefault((n, s[0]), []).append(i)
    hits = []
    for i in expl:
        s = out[i]
        if s[3] != "t" or _banned(s) or s[2] is None or s[2] >= 99: continue
        nb = {j for n in (s[5], s[6]) for j in at.get((n, s[0]), ()) if j != i}
        if any(_real(out[j]) and not _banned(out[j]) and out[j][2] == s[2] for j in nb): hits.append(i)
    for i in hits: out[i][3] = "o"
    return len(hits)
