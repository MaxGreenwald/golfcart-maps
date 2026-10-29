#!/usr/bin/env python3
"""Crawlable hubs that the home page links to, built like the other static SEO pages.

/golf-cart-maps  plural query ("golf cart maps"). Self-canonical. Home stays canonical at /.
/lsv             "LSV map app" / "low speed vehicle map". Self-canonical.

Neither page invents road rules: the town list and the 35 mph line come from regions.json and roadrule.js.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import *

# Query name -> region slug. All four already have a live map region (public/data + /map?r=).
MARKETS = [
    ("Hilton Head", "hiltonhead", "Hilton Head golf cart map"),
    ("The Villages", "villages", "The Villages golf cart map"),
    ("Gulf Shores", "gulfshores", "Gulf Shores golf cart map"),
    ("Naples", "naples", "Naples golf cart map"),
]
TOWNS = [
    ("Hilton Head Island", "/hiltonhead/hilton-head-island"),
    ("The Villages", "/villages/the-villages"),
    ("Gulf Shores", "/gulfshores/gulf-shores"),
    ("Orange Beach", "/gulfshores/orange-beach"),
    ("Naples", "/naples/naples"),
]


def _states(regs):
    by = {}
    for r in regs:
        by.setdefault(r["state"], []).append(r)
    return by


def _region_list(regs):
    by = _states(regs)
    out = []
    for st in sorted(by, key=lambda s: STATES.get(s, s)):
        items = "".join(
            f'<li><a href="/{e(r["slug"])}">{e(r["name"])} golf cart map</a></li>'
            for r in sorted(by[st], key=lambda r: r["name"]))
        out.append(f"<h2>{e(STATES.get(st, st))}</h2><ul>{items}</ul>")
    return "".join(out)


def _item_list(regs):
    ordered = sorted(regs, key=lambda r: (STATES.get(r["state"], r["state"]), r["name"]))
    return {"@context": "https://schema.org", "@type": "ItemList", "name": "Golf cart maps by town",
            "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                 "name": r["name"] + " golf cart map", "url": SITE + "/" + r["slug"]}
                                for i, r in enumerate(ordered)]}


def maps_page():
    regs = regions()
    n, ns = len(regs), len({r["state"] for r in regs})
    L = lsv_limits()
    title = f"Golf cart maps for {n} towns: the golf cart map | {BRAND}"
    desc = f"Golf cart maps for {n} beach and golf towns. Open a town golf cart map, or the LSV map, on {BRAND}." + POS.LANDING_DESC_TAIL
    faq = [
        ("Is it golf cart map or golf cart maps?",
         f"Both. {BRAND} (golfcartmap.com) is the golf cart map for {n} beach and golf towns. This page lists those golf cart maps."),
        ("Which towns have a golf cart map?",
         f"{n} beach and golf towns in {ns} states, from San Diego to The Villages, 30A, Hilton Head, Gulf Shores and Naples. Each link opens that town's page and its live map."),
        ("Is there an LSV map too?",
         "Yes. The LSV map app shows roads a street-legal low speed vehicle may use: roads " + lsv_line(L) + ", minus roads a town or county bans. A plain golf cart usually gets fewer roads."),
    ]
    markets = "".join(
        f'<li><a href="/{slug}">{e(anchor)}</a></li>' for _place, slug, anchor in MARKETS)
    towns = "".join(f'<li><a href="{e(url)}">{e(name)} golf cart map</a></li>' for name, url in TOWNS)
    body = f"""<nav aria-label="Breadcrumb" class="muted"><a href="/">Home</a> › Golf cart maps</nav>
<h1>Golf cart maps for {n} towns</h1>
<p>{BRAND} is the golf cart map for {n} beach and golf towns in {ns} states. This page lists the golf cart maps, one link per town. Free to use.</p>
<p><a class="cta" href="/" data-ev="cta_try_map_click" data-p='{{"position":"hub"}}'>Open Golf Cart Maps</a> <a href="/map">Open the map</a> · <a href="/lsv">LSV map app</a></p>
<h2>Golf cart map for a town</h2>
<p>These four are on the live map. Each link opens that town's golf cart map.</p>
<ul>{markets}</ul>
<h2>Town guides</h2><ul>{towns}</ul>
<h2>Every golf cart map</h2>
{_region_list(regs)}
<h2>FAQ</h2>
{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in faq)}"""
    webpage = {"@context": "https://schema.org", "@type": "CollectionPage", "name": title,
               "url": SITE + "/golf-cart-maps", "isPartOf": {"@id": SITE + "/#website"},
               "about": {"@id": SITE + "/#org"}}
    ld = [org(), website(), webpage, _item_list(regs), faq_schema(faq),
          crumbs([("Home", "/"), ("Golf cart maps", "/golf-cart-maps")])]
    return page(title, desc, "/golf-cart-maps", body, ld)


def lsv_page():
    regs = regions()
    n = len(regs)
    L = lsv_limits()
    line = lsv_line(L)
    title = f"LSV Map App: low speed vehicle map | {BRAND}"
    desc = f"LSV map app and low speed vehicle map for {n} beach and golf towns. Roads {line}. Free to use."
    if len(desc) > 180:
        desc = f"LSV map app and low speed vehicle map for {n} towns. Street-legal LSVs, with the local speed cap, on {BRAND}. Free to use."
    faq = [
        ("Is there an LSV map app?",
         f"Yes. {BRAND} is an LSV map app and a golf cart map. Pick LSV and it shows the roads a street-legal low speed vehicle may use: roads {line}, minus roads a town or county bans. It plans routes on them and works in any web browser."),
        ("What is a low speed vehicle map?",
         f"A low speed vehicle map shows where a registered LSV may drive. On this map that is roads {line}, unless a town or county bans that road."),
        ("Where can I drive my LSV?",
         "Usually on public roads posted 35 mph or less, if the LSV is registered, plated and insured. A few places set a lower limit, and towns or counties can ban an LSV from specific roads. Pick your town for the local rule and the law behind it."),
        ("What is the difference between a golf cart and an LSV?",
         "An LSV is street-legal: VIN, plate, insurance, 20 to 25 mph top speed. Most states allow LSVs on roads posted 35 mph or less. A plain golf cart usually gets fewer roads, and some towns allow it only on streets the city has designated."),
        ("Is it legal advice?", "No. Posted signs and local law always win."),
    ]
    markets = "".join(
        f'<li><a href="/map?r={e(next(r["id"] for r in regs if r["slug"]==slug))}&amp;veh=lsv">{e(place)} LSV map</a> (<a href="/{slug}">{e(place)} golf cart map</a>)</li>'
        for place, slug, _anchor in MARKETS)
    body = f"""<nav aria-label="Breadcrumb" class="muted"><a href="/">Home</a> › LSV map</nav>
<h1>LSV map app: low speed vehicle map</h1>
<p>{BRAND} is an LSV map app for street-legal low speed vehicles, and a golf cart map. Pick LSV and the map shows roads {e(line)}, minus roads a town or county bans. A plain golf cart usually gets fewer roads. Free to use. Posted signs win.</p>
<p><a class="cta" href="/map?veh=lsv" data-ev="cta_try_map_click" data-p='{{"position":"lsv"}}'>Open the LSV map</a> <a href="/golf-cart-maps">Golf cart maps</a></p>
<h2>35 mph, where that is the rule</h2>
<p>A street-legal LSV has a VIN, a plate and insurance, and a top speed of 20 to 25 mph. Many states allow it on roads posted 35 mph or less. This map does not use one national 35 mph rule. It uses roads {e(line)}. Local bans still win.</p>
<h2>Where can I drive my LSV?</h2>
<p>Open a town and pick LSV. The town page cites the statute or ordinance. These markets are on the live map:</p>
<ul>{markets}</ul>
<h2>Golf cart vs LSV</h2>
<p>The golf cart map and the LSV map are separate layers. An LSV is the street-legal vehicle. A plain golf cart is not, so most towns give it fewer roads. <a href="/">Golf Cart Maps</a> shows both, for {n} beach and golf towns.</p>
<p><a class="appstore" href="{TESTFLIGHT}"><img src="/download-on-the-app-store.svg" width="143" height="48" alt="Download on the App Store"></a> <small>iPhone app. The web map works in any browser.</small></p>
<h2>FAQ</h2>
{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in faq)}"""
    webpage = {"@context": "https://schema.org", "@type": "WebPage", "name": title,
               "url": SITE + "/lsv", "isPartOf": {"@id": SITE + "/#website"}}
    ld = [org(), website(), software(), webpage, faq_schema(faq),
          crumbs([("Home", "/"), ("LSV map", "/lsv")])]
    return page(title, desc, "/lsv", body, ld)


def build(out):
    open(os.path.join(out, "golf-cart-maps.html"), "w", encoding="utf-8").write(maps_page())
    open(os.path.join(out, "lsv.html"), "w", encoding="utf-8").write(lsv_page())


if __name__ == "__main__":
    print("maps", len(maps_page()), "lsv", len(lsv_page()))
