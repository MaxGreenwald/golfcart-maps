#!/usr/bin/env python3
"""The AEO landing page at / (dist/index.html). Static HTML, no map JS. Map moved to /map."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import *

FAQ = [
    ("Is Golf Cart Maps in beta? What does it cost?", "It's in beta, at no cost during the beta."),
    ("What is the difference between a golf cart and an LSV?", "A low-speed vehicle (LSV) is street-legal: it has a VIN, plate and insurance and meets federal FMVSS 500, with a top speed over 20 and at most 25 mph. Most states let LSVs use roads posted 35 mph or less. A plain golf cart usually gets fewer roads, often only ones a city or county has designated."),
    ("Which towns does Golf Cart Maps cover?", "%(n)d beach and golf towns across %(s)d states, from coastal San Diego to The Villages, 30A and Key West. See the list above."),
    ("Where do the rules come from?", "State vehicle codes and local ordinances, plus posted speed limits from city speed lists, street-level sign imagery (Mapillary) and OpenStreetMap. Each region page lists the law behind each rule. Unsigned small residential streets are assumed to be 25 mph."),
    ("Is it legal advice?", "No. Golf Cart Maps helps you plan. Posted signs and local law always win."),
    ("Does it work on my phone?", "Yes. It runs in any phone or desktop web browser, and an iPhone app is in App Store review."),
]

def render():
    regs = regions(); by = {}
    for r in regs: by.setdefault(r["state"], []).append(r)
    n, ns = len(regs), len(by)
    faq = [(q, a % {"n": n, "s": ns} if "%(" in a else a) for q, a in FAQ]
    title = "Golf Cart Maps: Legal Golf Cart & LSV Routes by Town (golfcartmap.com)"
    desc = f"See which roads golf carts and street-legal LSVs can use in {n} beach and golf towns, with the law behind each rule. Beta map and routes."
    cta = lambda pos: f'<a class="cta" href="/map" target="_blank" rel="noopener" data-ev="cta_try_map_click" data-p=\'{{"position":"{pos}"}}\'>Try the map</a>'
    lists = "".join(f"<h3>{e(STATES.get(st, st))}</h3><ul class=cols>" + "".join(f'<li><a href="/{r["slug"]}" data-ev="region_link_click" data-p=\'{{"region":"{e(r["id"])}"}}\'>{e(r["name"])}</a></li>' for r in sorted(by[st], key=lambda r: r["name"])) + "</ul>" for st in sorted(by, key=lambda s: STATES.get(s, s)))
    body = f"""<h1>Not just 35 mph and under. The roads your city actually allows.</h1>
<p>Golf Cart Maps (golfcartmap.com) is a golf cart and LSV map and navigation app, now in beta, that shows which roads your city and county actually allow, golf cart vs street-legal LSV, with the statute behind each rule. Available on the web for {n} towns as of {month()}.</p>
<p>{cta("hero")}</p>
<p><label><input type="checkbox" id="remember"> Always open the map when I visit</label></p>
<img src="/og-v4.png" width="1200" height="630" alt="Golf Cart Maps preview: legal roads in green, roads to avoid in red" style="width:100%;height:auto;border-radius:14px" loading="eager">
<h2 id="regions">Where can I drive a golf cart?</h2>
{lists}
<h2>How it works</h2>
<ol><li>Pick your vehicle: golf cart or street-legal LSV.</li><li>Pick a town and a destination.</li><li>Get a route on legal roads, with why each road is allowed.</li></ol>
<h2>How is Golf Cart Maps different from other golf cart apps?</h2>
<p>It depends on what you need. Most golf cart apps show cart paths or general routes; Golf Cart Maps focuses on the rules: which roads are allowed for your vehicle in each town, and the state law or local ordinance behind each one. <a href="/compare" data-ev="compare_link_click">See the comparison</a>.</p>
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
    return page(title, desc, "/", body, ld, head).replace("</body>", tail + "</body>")

if __name__ == "__main__":
    print(render()[:300])
