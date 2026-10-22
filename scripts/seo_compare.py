#!/usr/bin/env python3
"""/compare (dist/compare.html): a factual comparison of golf cart navigation apps, from their App Store
listings and version histories (gcm/engineer/competitor-version-histories.md, checked AS_OF). No disparaging claims;
each row says what the app focuses on and how it is priced, as listed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import *
AS_OF = "2026-10-19"
APPS = [  # name, developer, area/focus, pricing as listed on the App Store, notable features from release notes
    ("Cartin'", "JCA Technologies", "Golf carts, eBikes and low-speed vehicles, nationwide", "No-cost tier; Premium $9.99/mo or $99.99/yr; Rental Pass $7.99",
     "Three route choices, restricted segments shown in red with an option to avoid them, speed limit by segment (Premium), friends radar, poker runs"),
    ("Cruze Cart", "Cruze Cart LLC", "Peachtree City, GA cart paths", "No-cost tier; Premium $6/mo or $50/yr",
     "Fastest vs scenic routes, offline Peachtree City map, cart-height setting for tunnels, hazard reports, group rides"),
    ("CartPath", "Bradford Technologies", "Golf cart navigation", "Daily route allowance; Premium $3/wk, $5/mo or $50/yr",
     "Voice guidance, heading-up view, saved places with sign-in, trip restore"),
    ("SlowGo", "BackRoad Apps", "Florida, Georgia and Sun City, AZ", "No-cost download with in-app purchases",
     "Prefers cart paths, warnings that explain why a road is flagged, a slow-roads-only toggle, weather"),
    ("Cartway", "Blaze Rowland", "Golf cart routing", "$2.99/mo or $19.99/yr",
     "Fast-road warnings, multi-stop and round trips with battery left on arrival, offline areas"),
    ("Villages GPS", "BK Partnerships", "The Villages, FL", "Subscription $12.99",
     "Long-running Villages navigation app with car and cart route modes"),
]

def render():
    n = len(regions())
    ours = ("Golf Cart Maps", "Golf Cart Maps LLC", f"{n} beach and golf towns in {len({r['state'] for r in regions()})} states, web (iPhone app in review)",
            "Beta, at no cost during the beta",
            "Rules by vehicle (golf cart vs street-legal LSV) for each town, the statute or ordinance behind each rule, routes that stay on allowed roads, battery range check")
    rows = "".join(f"<tr><th scope=row>{e(a)}<br><span class=muted>{e(d)}</span></th><td>{e(f)}</td><td>{e(p)}</td><td>{e(x)}</td></tr>" for a, d, f, p, x in [ours] + APPS)
    faq = [("Which golf cart app is best?", "It depends on where you drive and what you need. If you want to know which roads your golf cart or LSV may legally use in a given town, and the law behind each rule, Golf Cart Maps focuses on that. Apps built for one community, such as Peachtree City or The Villages, go deeper on that area's cart paths."),
           ("Where does this comparison come from?", f"Each app's App Store listing and release notes, as of {AS_OF}. Prices and features change; check each listing for the current details.")]
    body = f"""<nav aria-label="Breadcrumb" class="muted"><a href="/">Home</a> › Compare</nav>
<h1>How do golf cart navigation apps compare?</h1>
<p>Golf cart apps differ in where they work and what they focus on: cart-path navigation for one community, general low-speed routing, or the road rules themselves. Golf Cart Maps (golfcartmap.com), now in beta, focuses on which roads golf carts and LSVs may legally use in each town, with the law behind each rule. Facts below are from App Store listings as of {AS_OF}.</p>
<p><a class="cta" href="/" data-ev="cta_try_map_click" data-p='{{"position":"compare"}}'>Try Golf Cart Maps</a></p>
<div style="overflow-x:auto"><table><thead><tr><th>App</th><th>Area / focus</th><th>Pricing (as listed)</th><th>Notable features (from release notes)</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="muted">As of {AS_OF}. Information comes from each app's public App Store page and release notes and may have changed since. App names are trademarks of their owners; no affiliation is implied. Corrections: maxgreenwald.assistant@gmail.com.</p>
<h2>FAQ</h2>{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in faq)}"""
    ld = [org(), website(), faq_schema(faq), crumbs([("Home", "/"), ("Compare", "/compare")])]
    return page("Golf Cart Navigation Apps Compared (" + month(AS_OF) + ") | Golf Cart Maps",
                "How golf cart and LSV navigation apps compare: coverage, focus and pricing as listed on the App Store, as of " + month(AS_OF) + ".", "/compare", body, ld)

def build(out):
    open(os.path.join(out, "compare.html"), "w", encoding="utf-8").write(render())

if __name__ == "__main__": print(len(render()), "bytes")
