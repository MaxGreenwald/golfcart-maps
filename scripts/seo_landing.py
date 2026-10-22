#!/usr/bin/env python3
"""The AEO landing page at / (dist/index.html). Static HTML, no map JS. Map moved to /map."""
import os, sys, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import *

FAQ = [
    (POS.COST_Q, POS.COST_A),
    ("Which towns does Golf Cart Maps cover?", "%(n)d beach and golf towns in %(s)d states, from San Diego to The Villages, 30A and Key West."),
    ("What is the difference between a golf cart and an LSV?", "An LSV is street-legal: VIN, plate, insurance, 20 to 25 mph top speed. Most states allow LSVs on roads posted 35 mph or less. Plain golf carts usually get fewer roads."),
    ("Where do the rules come from?", "State vehicle codes, local ordinances and posted speed limits. Each town page cites the law behind each rule."),
    ("Is it legal advice?", "No. Posted signs and local law always win."),
    ("Does it work on my phone?", "Yes, in any phone or desktop browser. An iPhone app is in App Store review."),
]
PARTNER = "mailto:max@golfcartmap.com?subject=Partner%20with%20Golf%20Cart%20Maps"
LCSS = (".hero h1{font-size:40px;line-height:1.1}.hero h1+p{font-size:20px}"
        ".stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:22px 0;padding:18px;background:#0b6e86;color:#fff;border-radius:16px;text-align:center}"
        ".stats b{display:block;font-size:30px;line-height:1.1}.stats span{font-size:13px;opacity:.9}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;padding:0;list-style:none}"
        ".grid li a{display:block;padding:10px 12px;border:1px solid #cfe5ea;border-radius:12px;text-decoration:none;font-weight:700;background:#fff}"
        ".grid li a small{display:block;font-weight:400;color:#5a7684}.towns{font-size:15px}"
        ".band{padding:22px;border-radius:16px;margin:26px 0}.oem{background:#17384a;color:#fff}.oem a{color:#9fe7f0}.shops{background:#e6fbfc}"
        "@media(max-width:600px){.hero h1{font-size:31px}.stats{grid-template-columns:repeat(2,1fr)}.stats b{font-size:24px}}")

def stats():
    """Real numbers only, computed from public/data at build time (scripts/site_stats.js)."""
    import subprocess
    st = json.loads(subprocess.run(["node", os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_stats.js")], capture_output=True, text=True, check=True).stdout)
    towns = [t for t in (json.load(open(f)) for f in sorted(glob.glob(os.path.join(ROOT, "content", "towns", "*", "*.json"))))]
    return st, towns

def render():
    regs = regions(); by = {}
    for r in regs: by.setdefault(r["state"], []).append(r)
    n, ns = len(regs), len(by)
    st, towns = stats()
    faq = [(q, a % {"n": n, "s": ns} if "%(" in a else a) for q, a in FAQ]
    title = "Golf Cart Maps: Every Legal Golf Cart & LSV Road on One Map (golfcartmap.com)"
    desc = f"Cruise anywhere your cart is legal. Every legal golf cart and LSV road in {n} beach and golf towns, with the law behind each rule." + POS.LANDING_DESC_TAIL
    cta = lambda pos: f'<a class="cta" href="/map" target="_blank" rel="noopener" data-ev="cta_try_map_click" data-p=\'{{"position":"{pos}"}}\'>Open the map</a>'
    k = lambda x: f"{x:,}"
    grid = "".join(f'<li><a href="/{r["slug"]}" data-ev="region_link_click" data-p=\'{{"region":"{e(r["id"])}"}}\'>{e(r["name"])}<small>{e(STATES.get(r["state"], r["state"]))}</small></a></li>' for r in sorted(regs, key=lambda r: (STATES.get(r["state"], r["state"]), r["name"])))
    tl = " · ".join(f'<a href="/{e(t["region"])}/{e(t["slug"])}">{e(t["name"])}</a>' for t in sorted(towns, key=lambda t: t["name"]))
    body = f"""<section class="hero"><h1>Cruise anywhere your cart is legal.</h1>
<p>Every legal golf cart and LSV road, on one map. Pick a town, pick a place, and ride roads your city actually allows.</p>
<p>{cta("hero")}</p>
<p><label><input type="checkbox" id="remember"> Always open the map when I visit</label></p></section>
<div class="stats" role="list"><div role="listitem"><b>{k(st["road_mi"])}</b><span>road miles mapped</span></div><div role="listitem"><b>{n}</b><span>regions live</span></div><div role="listitem"><b>{ns}</b><span>states</span></div><div role="listitem"><b>{len(towns)}</b><span>town guides</span></div></div>
<img src="/og-v4.png" width="1200" height="630" alt="Golf Cart Maps: legal roads in green, roads to avoid in red" style="width:100%;height:auto;border-radius:14px" loading="eager">
<!-- Trusted by: empty on purpose. Add partner names or logos only with that partner's written permission. -->
<h2 id="regions">Where can I drive a golf cart?</h2>
<p>Live in {n} regions, from San Diego to The Villages, 30A, Hilton Head and Hawaii.</p>
<ul class="grid">{grid}</ul>
<h3>Town guides</h3><p class="towns">{tl}</p>
<section class="band oem"><h2>For manufacturers and OEMs</h2>
<p>We work with cart manufacturers and OEMs to bring legal-road maps to in-dash screens: town-by-town road rules for golf carts and LSVs, with the law behind each one.</p>
<p><a class="cta" href="{PARTNER}" data-ev="partner_click" data-p=\'{{"section":"oem"}}\'>Partner with us</a></p></section>
<section class="band shops"><h2>For shops and dealers</h2>
<p>Send renters and buyers off the lot with a map of where they can legally ride. Spot a wrong road in your town? Tell us and we fix it.</p>
<p><a href="{PARTNER}" data-ev="partner_click" data-p=\'{{"section":"shops"}}\'>Work with us: max@golfcartmap.com</a></p></section>
<h2>FAQ</h2>
{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in faq)}
<p>{cta("footer")}</p>"""
    ld = [org(), website(), software(), faq_schema(faq)]
    head = ("<script>if(window.Capacitor||/^(capacitor|ionic):/.test(location.protocol))location.replace('map.html'+location.search);"
            "else if(location.hash.length>1){document.cookie='gcm_rd=hash; Max-Age=60; Path=/';location.replace('/map'+location.search+location.hash)}"
            "else{try{if(localStorage.getItem('gcm_skip_landing')==='1'&&!/[?&]stay=1/.test(location.search)){document.cookie='gcm_rd=cookie; Max-Age=60; Path=/';location.replace('/map'+location.search)}}catch(_){}}</script>")
    tail = ("<script>addEventListener('load',function(){var T=window.GCMTrack,c=document.getElementById('remember');try{c.checked=localStorage.getItem('gcm_skip_landing')==='1'}catch(_){}"
            "T&&T.track('landing_view',{});c.onchange=function(){try{if(c.checked){localStorage.setItem('gcm_skip_landing','1');document.cookie='gcm_skip=1; Max-Age=31536000; Path=/; SameSite=Lax'}else{localStorage.removeItem('gcm_skip_landing');document.cookie='gcm_skip=; Max-Age=0; Path=/'}}catch(_){}T&&T.track('remember_map_toggle',{on:c.checked})};"
            "document.querySelectorAll('a.cta').forEach(function(a){a.addEventListener('click',function(){try{sessionStorage.setItem('gcm_from_landing','1')}catch(_){}})})})</script>")
    return page(title, desc, "/", body, ld, head + "<style>" + LCSS + "</style>").replace("</body>", tail + "</body>")

if __name__ == "__main__":
    print(render()[:300])
