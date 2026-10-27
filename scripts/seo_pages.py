#!/usr/bin/env python3
"""Prerender one static page per region at build time: dist/<slug>.html (served at /<slug>).
Rules text is computed by public/roadrule.js (seo_common.effective_rules), so it matches the map.
Called by build_web.py; `seo_pages.py --check` renders everything and exits 1 on a problem."""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import *

# Markets Gary flagged (2026-W44): a live map region already exists, so these pages link to it.
# Place names are the query names ("Hilton Head"), which are shorter than the region name.
MARKETS = {
    "hiltonhead": "Hilton Head",
    "villages": "The Villages",
    "gulfshores": "Gulf Shores",
    "naples": "Naples",
}

# Primary sources checked 2026-10-26. Ordinance numbers and dates only where the city or Municode page states them.
# Cotton Bay streets are named in the April 13, 2026 city copy; that copy's ordinance number is blank, and Municode
# titles the same April 13, 2026 designated-street amendment as Ordinance No. 2210. Do not treat 2210 as a new road rule.
GULF_FRESH = """<h2>Recent ordinances</h2>
<p>The table above is what the map uses. These links are the city documents, not a second set of road rules. Posted signs win.</p>
<ul>
<li>Gulf Shores <a href="https://library.municode.com/al/gulf_shores/ordinances/code_of_ordinances?nodeId=1420654" rel="nofollow">Ordinance No. 2210</a> (adopted April 13, 2026) amends Sec. 21-13 designated cart streets. The <a href="https://www.gulfshoresal.gov/AgendaCenter/ViewFile/Item/15531?fileID=45381" rel="nofollow">April 13, 2026 city copy</a> adds streets in the Aventura subdivision and restates the designated list, which includes the Cotton Bay subdivision (Cotton Bay Blvd, Savannah Lane, Plantation Lane, Cotton Bay Lane, Cotton Bay Dr West, Cotton Bay Dr East, and Cotton Bay Court). Cotton Bay streets were added by the <a href="https://www.gulfshoresal.gov/AgendaCenter/ViewFile/Agenda/_01122026-1112?packet=true" rel="nofollow">January 12, 2026 ordinance</a>.</li>
<li>A separate <a href="https://www.gulfshoresal.gov/AgendaCenter/ViewFile/Item/15481?fileID=45110" rel="nofollow">April 13, 2026 ordinance</a> rewrites Sec. 21-13(c) and keeps state-tagged carts off streets posted over 25 mph.</li>
<li>Orange Beach <a href="https://library.municode.com/al/orange_beach/ordinances/code_of_ordinances?nodeId=2025" rel="nofollow">Ordinance No. 2025-1521</a> amends Chapter 70, Article VIII (Golf Carts). Municode lists it as adopted November 3, 2025; the code history dates the amendment November 4, 2025. Current text: <a href="https://library.municode.com/al/orange_beach/codes/code_of_ordinances?nodeId=COOR_CH70TRVE_ARTVIIIGOCA_S70-273DE" rel="nofollow">Chapter 70, Article VIII</a>.</li>
</ul>"""


def town_links(slug):
    d = os.path.join(ROOT, "content", "towns", slug)
    if not os.path.isdir(d): return ""
    items = []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        t = json.load(open(f, encoding="utf-8"))
        items.append(f'<li><a href="/{e(slug)}/{e(t["slug"])}">{e(t["name"])} golf cart map</a></li>')
    return "<h2>Town guides</h2><ul>" + "".join(items) + "</ul>" if items else ""

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
    out.append((f"Where can I drive my LSV in {n}?", f"{lsv_a} Source: {l.get('cite','state law')}. A town or county can still ban LSVs from a specific road, and posted signs win. Pick LSV on the {n} LSV map and {BRAND} shows allowed roads in green and roads to avoid in red."))
    out.append((f"Can I drive a golf cart on the street in {n}?", f"{vrow('', c)[1]} Source: {c.get('cite','state law')}."))
    out.append((f"What is the difference between a golf cart and an LSV in {st}?", "A low-speed vehicle (LSV) is a street-legal vehicle with a VIN, plate and insurance that meets federal FMVSS 500 (top speed over 20 and at most 25 mph). A plain golf cart has none of that, so most states limit it to fewer roads."))
    out.append(("Where do the rules come from?", "State vehicle codes and local ordinances, plus posted speed limits from city speed lists, street-level sign imagery (Mapillary) and OpenStreetMap. Unsigned small residential streets are assumed to be 25 mph. Posted signs always win."))
    out.append((f"Is {BRAND} legal advice?", "No. It's a map to help you plan; always follow posted signs."))
    return out

RES = os.path.join(ROOT, "content", "region_resources.json")

def region_resources(slug, path=RES):
    """Local resources for a region page: content/region_resources.json maps region slug -> [{lead, name, url}] (followed links)."""
    return json.load(open(path, encoding="utf-8")).get(slug, []) if os.path.exists(path) else []

def resources_html(items):
    lis = "".join(f"<li>{e(r['lead'])} See <a href=\"{e(r['url'])}\">{e(r['name'])}</a>.</li>" for r in items)
    return f"<h2>Local resources</h2><ul>{lis}</ul>" if lis else ""

def region_page(g, R):
    n, st, slug = g["name"], STATES.get(g["state"], g["state"]), g["slug"]
    place = MARKETS.get(slug)
    title = (f"{BRAND}: {place} golf cart map and LSV map ({month()})" if place
             else f"{n} Golf Cart Map & LSV Map: Rules and Legal Roads ({month()})")
    lsv, cart = vrow("Street-legal LSV", R["lsv"]), vrow("Golf cart", R["golf_cart"])
    desc = f"Where golf carts and LSVs can legally drive in {n}: LSVs on roads posted {R['lsv'].get('max_posted','?')} mph or less ({R['lsv'].get('cite','state law').split(' (')[0]}). Golf cart and LSV map with routes."
    if len(desc) > 155: desc = desc[:152].rsplit(" ", 1)[0] + "..."
    mapurl = f"/map?r={g['id']}"
    faq = faq_for(g, R)
    rows = "".join(f"<tr><th scope=row>{e(a)}</th><td>{e(b)}</td><td>{e(c)}{(' <a href=\"'+e(u)+'\" rel=nofollow>source</a>') if u else ''}</td></tr>" for a, b, c, u in (lsv, cart))
    h1 = (f"{place} golf cart maps: where can you drive a golf cart or LSV?" if place
          else f"Where can you drive a golf cart or LSV in {n}?")
    market = ""
    if place:
        lsvurl = f"/map?r={g['id']}&veh=lsv"
        market = f"""<p>This {e(place)} golf cart map is on {BRAND} (golfcartmap.com). The <a href="{e(lsvurl)}">{e(place)} LSV map</a> is the same roads colored for a street-legal low speed vehicle. <a href="/golf-cart-maps">All golf cart maps</a>.</p>
{town_links(slug)}
{GULF_FRESH if slug == "gulfshores" else ""}"""
    body = f"""<nav aria-label="Breadcrumb" class="muted"><a href="/">Home</a> › <a href="/golf-cart-maps">Golf cart maps</a> › {e(st)} › {e(n)}</nav>
<h1>{e(h1)}</h1>
<p>{e(lsv[1])} Plain golf carts: {e(cart[1][0].lower()+cart[1][1:])} The {e(g['short'] or n)} golf cart map and LSV map on {BRAND} (golfcartmap.com) colors every road and plans routes that stay on legal ones. Rules last checked {e(month())}.</p>
<p><a class="cta" href="{mapurl}" data-ev="cta_try_map_click" data-p='{{"position":"region","region":"{e(g['id'])}"}}'>Open the {e(g['short'] or n)} map</a></p>
{market}<h2>The rules in {e(n)}</h2>
<table><thead><tr><th>Vehicle</th><th>Where it may drive</th><th>Law</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Coverage</h2><p>{e(g.get('cover',''))}</p>
<h2>FAQ</h2>
{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in faq)}
{resources_html(region_resources(slug))}
<p><a class="cta" href="{mapurl}" data-ev="cta_try_map_click" data-p='{{"position":"footer","region":"{e(g['id'])}"}}'>Open the {e(g['short'] or n)} map</a></p>"""
    ld = [org(), website(), software(), faq_schema(faq), crumbs([("Home", "/"), ("Golf cart maps", "/golf-cart-maps"), (n, "/" + slug)])]
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
