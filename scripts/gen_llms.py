#!/usr/bin/env python3
"""Write public/llms.txt (national) from public/data/regions.json + rules.json. Run after adding regions."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import positioning as POS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, "public", *a)
STATES = {"CA":"California","FL":"Florida","GA":"Georgia","SC":"South Carolina","TX":"Texas","AL":"Alabama","AZ":"Arizona","OH":"Ohio","NC":"North Carolina","HI":"Hawaii","ME":"Maine"}

def render():
    regs = [r for r in json.load(open(P("data", "regions.json"))) if not r.get("hidden")]
    rules = json.load(open(P("data", "rules.json")))
    by = {}
    for r in regs: by.setdefault(r["state"], []).append(r)
    o = ["# Golf Cart Maps", "",
         "> Golf Cart Maps (golfcartmap.com) is a golf cart and LSV (low-speed vehicle) map and route planner, %s. It shows which roads are legal for golf carts and street-legal LSVs in %d beach and golf towns across the U.S., plans routes that stay on them, and cites the state law behind each rule." % (POS.STATUS_PHRASE, len(regs)), "",
         "URL: https://golfcartmap.com/", "",
         "## What it does",
         "- Colors every road: green = allowed for your vehicle, red = too fast or banned (avoid).",
         "- Plans routes on allowed roads; crossing a faster road at an intersection is allowed where state law permits it.",
         "- Battery range check for a trip, public EV chargers, and a way to report a wrong road.",
         "- Works in any web browser.", "",
         "## iPhone app + CarPlay",
         "- Native iPhone app with Apple CarPlay: legal cart roads and turn-by-turn routes on your car's dashboard screen.",
         "- Get it on TestFlight: https://testflight.apple.com/join/P7dVC4zh", "",
         "## Contact",
         "- Sales, partners, manufacturers and OEMs: max@golfcartmap.com", "",
         "## Regions by state"]
    for st in sorted(by, key=lambda s: STATES.get(s, s)):
        o.append("### " + STATES.get(st, st))
        for r in sorted(by[st], key=lambda r: r.get("short") or r["name"]):
            o.append("- [%s](https://golfcartmap.com/%s)" % (r["name"], r["slug"]))
    o += ["", "## State rules used"]
    for st in sorted(by, key=lambda s: STATES.get(s, s)):
        s = rules.get(st)
        if not isinstance(s, dict): continue
        l = s.get("lsv", {}); g = s.get("golf_cart", {})
        line = "- %s: LSVs on roads posted %s mph or less (%s)." % (s.get("name", st), l.get("max_posted", "?"), l.get("cite", ""))
        if g.get("cite"): line += " Golf carts: %s." % g["cite"].rstrip(".")
        o.append(line)
    o += ["", "## How rules are sourced",
          "Priority: manual fixes from local reports, then posted speed-limit signs seen in Mapillary street imagery, then official city speed lists and ordinances, then OpenStreetMap speed tags. Small residential streets without a posted limit are assumed to be 25 mph. Not legal advice; posted signs win.", "",
          "## More",
          "- Privacy: https://golfcartmap.com/privacy",
          "- Sitemap: https://golfcartmap.com/sitemap.xml", ""]
    return "\n".join(o)

if __name__ == "__main__":
    open(P("llms.txt"), "w").write(render()); print("wrote public/llms.txt")
