#!/usr/bin/env python3
"""Prerender one static page per region at build time: dist/<slug>.html (served at /<slug>).
Rules text is computed by public/roadrule.js (seo_common.effective_rules), so it matches the map.
Called by build_web.py; `seo_pages.py --check` renders everything and exits 1 on a problem."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import *

def vrow(label, r):
    if r.get("not_street_legal") or not r.get("max_posted"):
        line = "Not allowed on public roads here."
    else:
        line = "Roads posted %d mph or less" % r["max_posted"]
        if r.get("designated_only"): line += ", and only on roads the city or county has designated"
        line += "." + (" May cross faster roads at intersections." if r.get("cross") else " No crossing faster roads except at marked crossings or tunnels.")
        if r.get("daylight_only"): line += " Daylight only unless equipped."
    note = (" " + r["note"].rstrip(".") + ".") if r.get("note") else ""
    return label, line + note, r.get("cite", ""), r.get("url")

def faq_for(g, R):
    n, st = g["short"] or g["name"], STATES.get(g["state"], g["state"])
    l, c = R["lsv"], R["golf_cart"]
    out = []
    lsv_a = vrow("", l)[1]
    out.append((f"Where can I drive an LSV in {n}?", f"{lsv_a} Source: {l.get('cite','state law')}. {BRAND} shows allowed roads in green and roads to avoid in red."))
    out.append((f"Can I drive a golf cart on the street in {n}?", f"{vrow('', c)[1]} Source: {c.get('cite','state law')}."))
    out.append((f"What is the difference between a golf cart and an LSV in {st}?", "A low-speed vehicle (LSV) is a street-legal vehicle with a VIN, plate and insurance that meets federal FMVSS 500 (top speed over 20 and at most 25 mph). A plain golf cart has none of that, so most states limit it to fewer roads."))
    out.append(("Where do the rules come from?", "State vehicle codes and local ordinances, plus posted speed limits from city speed lists, street-level sign imagery (Mapillary) and OpenStreetMap. Unsigned small residential streets are assumed to be 25 mph. Posted signs always win."))
    out.append((f"Is {BRAND} legal advice?", "No. It's a map to help you plan; always follow posted signs."))
    return out

def region_page(g, R):
    n, st, slug = g["name"], STATES.get(g["state"], g["state"]), g["slug"]
    title = f"Golf Cart & LSV Rules and Legal Roads in {n} ({month()})"
    lsv, cart = vrow("Street-legal LSV", R["lsv"]), vrow("Golf cart", R["golf_cart"])
    desc = f"Where golf carts and LSVs can legally drive in {n}: LSVs on roads posted {R['lsv'].get('max_posted','?')} mph or less ({R['lsv'].get('cite','state law').split(' (')[0]}). Legal-road map and routes."
    if len(desc) > 155: desc = desc[:152].rsplit(" ", 1)[0] + "..."
    mapurl = f"/map?r={g['id']}"
    faq = faq_for(g, R)
    rows = "".join(f"<tr><th scope=row>{e(a)}</th><td>{e(b)}</td><td>{e(c)}{(' <a href=\"'+e(u)+'\" rel=nofollow>source</a>') if u else ''}</td></tr>" for a, b, c, u in (lsv, cart))
    body = f"""<nav aria-label="Breadcrumb" class="muted"><a href="/">Home</a> › {e(st)} › {e(n)}</nav>
<h1>Where can you drive a golf cart or LSV in {e(n)}?</h1>
<p>{e(lsv[1])} Plain golf carts: {e(cart[1][0].lower()+cart[1][1:])} {BRAND} (golfcartmap.com) maps every road in {e(n)} and plans routes that stay on legal ones. Rules last checked {e(month())}.</p>
<p><a class="cta" href="{mapurl}" data-ev="cta_try_map_click" data-p='{{"position":"region","region":"{e(g['id'])}"}}'>Open the {e(g['short'] or n)} map</a></p>
<h2>The rules in {e(n)}</h2>
<table><thead><tr><th>Vehicle</th><th>Where it may drive</th><th>Law</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Coverage</h2><p>{e(g.get('cover',''))}</p>
<h2>FAQ</h2>
{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in faq)}
<p><a class="cta" href="{mapurl}" data-ev="cta_try_map_click" data-p='{{"position":"footer","region":"{e(g['id'])}"}}'>Open the {e(g['short'] or n)} map</a></p>"""
    ld = [org(), website(), software(), faq_schema(faq), crumbs([("Home", "/"), (n, "/" + slug)])]
    # old share links with map state (?lat, ?lon, ?veh, ?z, ?r) go straight to the map
    head = f"<script>(function(q){{if(/[?&](lat|lon|veh|z|r|paid)=/.test(q))location.replace('/map?r={g['id']}'+(q?'&'+q.slice(1):''))}})(location.search)</script>"
    return page(title, desc, "/" + slug, body, ld, head)

def build(out):
    R = effective_rules(); n = 0
    for g in regions():
        open(os.path.join(out, g["slug"] + ".html"), "w", encoding="utf-8").write(region_page(g, R[g["id"]])); n += 1
    return n

if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as t: print("rendered", build(t), "region pages")
