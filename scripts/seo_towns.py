#!/usr/bin/env python3
"""Render town pages from content/towns/<region>/<town>.json to dist/<region>/<town>.html (served at /<region>/<town>),
and add them to dist/sitemap.xml with lastmod = last_checked. content/towns/_example.json renders to /_preview/ (noindex)."""
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import *
TOWNS = os.path.join(ROOT, "content", "towns")
REQ = ["slug","region","name","state","question_title","answer_short","golf_cart","lsv","rules","faq","map_center","zoom","published","last_checked"]

def check(t, path):
    miss = [k for k in REQ if k not in t]
    if miss: raise SystemExit(f"{path}: missing {miss}")
    if len(t["answer_short"].split()) > 60: raise SystemExit(f"{path}: answer_short is over 60 words")
    for k in ("published", "last_checked"):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", t[k]): raise SystemExit(f"{path}: {k} must be YYYY-MM-DD")

def town_page(t, reg, path, noindex=False):
    rslug, n = t["region"], t["name"]
    url = f"/{rslug}/{t['slug']}"
    lat, lon = t["map_center"]
    mapurl = f"/map/{rslug}?lat={lat}&lon={lon}&z={t['zoom']}"
    faq = [(f["q"], f["a"]) for f in t["faq"]]
    veh = lambda lab, v: f"<tr><th scope=row>{lab}</th><td>{e(v.get('allowed',''))}</td><td>{e(v.get('roads',''))}</td><td>{e(v.get('speed_line',''))}</td><td>{e(v.get('notes',''))}</td></tr>"
    rules = "".join(f"<tr><td>{e(r['topic'])}</td><td>{e(r['rule'])}</td><td><a href=\"{e(r['source_url'])}\" rel=nofollow>{e(r['citation'])}</a></td></tr>" for r in t["rules"])
    banned = "".join(f"<li>{e(b['name'])}: {e(b['rule'])}{' (crossing at intersections OK)' if b.get('crossings_ok') else ''}</li>" for b in t.get("banned_roads", []))
    shops = "".join(f"<li><a href=\"{e(s['url'])}\" rel=nofollow>{e(s['name'])}</a></li>" for s in t.get("rental_shops", []))
    res = "".join(f"<li>{e(r['lead'])} See <a href=\"{e(r['url'])}\">{e(r['name'])}</a>.</li>" for r in t.get("local_resources", []))
    near = "".join(f"<li><a href=\"/{rslug}/{e(s)}\">{e(s.replace('-', ' ').title())}</a></li>" for s in t.get("nearby", []))
    body = f"""<nav aria-label="Breadcrumb" class="muted"><a href="/">Home</a> › <a href="/{rslug}">{e(reg['name'])}</a> › {e(n)}</nav>
<h1>{e(t['question_title'])}</h1>
<p>{e(t['answer_short'])}</p>
<p class="muted checked">Rules last checked {e(t['last_checked'])}{(' by ' + e(t['checked_by'])) if t.get('checked_by') else ''}. Published {e(t['published'])}.</p>
<table><thead><tr><th>Vehicle</th><th>Allowed</th><th>Roads</th><th>Speed</th><th>Notes</th></tr></thead><tbody>{veh('Golf cart', t['golf_cart'])}{veh('Street-legal LSV', t['lsv'])}</tbody></table>
<h2>The rules</h2><table><thead><tr><th>Topic</th><th>Rule</th><th>Law</th></tr></thead><tbody>{rules}</tbody></table>
{('<h2>Roads to avoid</h2><ul>' + banned + '</ul>') if banned else ''}
<p><a class="cta" href="{e(mapurl)}" data-ev="cta_try_map_click" data-p='{{"position":"town","region":"{e(reg['id'])}"}}'>Open the live {e(n)} golf cart map in {BRAND} (golfcartmap.com)</a></p>
{('<h2>FAQ</h2>' + ''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in faq)) if faq else ''}
{('<h2>Golf cart rentals</h2><ul>' + shops + '</ul>') if shops else ''}
{('<h2>Local resources</h2><ul>' + res + '</ul>') if res else ''}
{('<h2>Nearby towns</h2><ul>' + near + '</ul>') if near else ''}
<p class="muted">Not legal advice; posted signs win.</p>"""
    webpage = {"@context":"https://schema.org","@type":"WebPage","name":t["question_title"],"url":SITE+url,"datePublished":t["published"],"dateModified":t["last_checked"],"isPartOf":{"@id":SITE+"/#website"}}
    ld = [webpage, crumbs([("Home", "/"), (reg["name"], "/" + rslug), (n, url)])] + ([faq_schema(faq)] if faq else [])
    # seo_title is optional and only for pages whose question already names the place and the vehicle.
    # It does not replace the H1 (question_title). Leave it off pages with no map/LSV hook.
    title = (f"{t['seo_title']} | {BRAND} ({month(t['last_checked'])})" if t.get("seo_title")
             else f"{t['question_title']} Rules and legal roads ({month(t['last_checked'])})")
    return page(title, t["answer_short"][:152].rsplit(" ", 1)[0] + ("..." if len(t["answer_short"]) > 152 else ""), url, body, ld,
                '<meta name="robots" content="noindex">' if noindex else "")

def build(out, root=TOWNS):
    regs = {r["slug"]: r for r in regions()}; made = []
    files = sorted(glob.glob(os.path.join(root, "*", "*.json")))
    for f in files + [os.path.join(root, "_example.json")]:
        if not os.path.exists(f): continue
        t = json.load(open(f)); check(t, f)
        if t["region"] not in regs: raise SystemExit(f"{f}: unknown region {t['region']}")
        ex = f.endswith("_example.json")
        if not ex and os.path.basename(os.path.dirname(f)) != t["region"]: raise SystemExit(f"{f}: folder must be the region slug")
        d = os.path.join(out, "_preview" if ex else t["region"]); os.makedirs(d, exist_ok=True)
        name = "town-example.html" if ex else t["slug"] + ".html"
        open(os.path.join(d, name), "w", encoding="utf-8").write(town_page(t, regs[t["region"]], f, noindex=ex))
        if not ex: made.append(t)
    sm = os.path.join(out, "sitemap.xml")
    if made and os.path.exists(sm):
        x = open(sm).read()
        add = "".join(f"<url><loc>{SITE}/{t['region']}/{t['slug']}</loc><lastmod>{t['last_checked']}</lastmod></url>" for t in made)
        open(sm, "w").write(x.replace("</urlset>", add + "</urlset>"))
    return made

if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as t: print("rendered", len(build(t)), "town pages (+ example preview)")
