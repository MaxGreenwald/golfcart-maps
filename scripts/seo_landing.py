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
    ("Is there an LSV map app?", "Yes. Golf Cart Maps is an LSV map app as well as a golf cart map. Pick LSV and it shows the roads a street-legal low speed vehicle may use: roads %(lsv)s, minus roads a town or county bans. It plans routes on them and works in any web browser."),
    ("Where can I drive my LSV?", "Usually on public roads posted 35 mph or less, if the LSV is registered, plated and insured. A few places set a lower limit, and towns or counties can ban an LSV from specific roads. Pick your town on the map or open its page for the local rule and the law behind it."),
    ("Is it Golf Cart Map or Golf Cart Maps?", "Both. Golf Cart Maps (https://golfcartmap.com/golf-cart-maps) is the golf cart map for %(n)d beach and golf towns, including the LSV map for street-legal low speed vehicles. People search golf cart map and golf cart maps; both are this site."),
    ("Is it legal advice?", "No. Posted signs and local law always win."),
    ("Is there an iPhone app with CarPlay?", "Yes. The iPhone app shows legal cart roads and routes on your phone and on your CarPlay dashboard screen. Download it on the App Store; the web map works in any browser."),
]
LCSS = (".appstore{display:inline-block;vertical-align:middle;line-height:0}.appstore img{display:block}"
        ".hero{display:grid;grid-template-columns:1.05fr .95fr;gap:28px;align-items:center;margin-top:8px}"
        ".hero-copy .pill{display:inline-block;background:#ffe9a8;color:#5a4500;font-weight:700;font-size:13px;padding:6px 12px;border-radius:999px;margin-bottom:10px}"
        ".hero h1{font-size:40px;line-height:1.12;margin:.15em 0 .35em;color:#0b3d4d}"
        ".hero .sub{font-size:19px;line-height:1.45;color:#355968;margin:0 0 16px}"
        ".find{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px;position:relative}"
        ".find input{flex:1;min-width:200px;padding:12px 14px;border:1px solid #b7d5dc;border-radius:12px;font:inherit}"
        ".find button{background:#0b7d91;color:#fff;border:0;border-radius:12px;padding:12px 16px;font-weight:800;cursor:pointer}"
        ".find-list{position:absolute;left:0;right:0;top:100%;z-index:5;background:#fff;border:1px solid #cfe5ea;border-radius:12px;margin:4px 0 0;padding:0;list-style:none;max-height:240px;overflow:auto;box-shadow:0 8px 24px rgba(23,56,74,.12);display:none}"
        ".find-list li button{display:block;width:100%;text-align:left;background:#fff;color:#17384a;border:0;border-bottom:1px solid #eef5f7;border-radius:0;padding:10px 14px;font-weight:600;cursor:pointer}"
        ".find-list li button:hover,.find-list li button:focus{background:#e6fbfc}"
        ".hero-actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:4px 0 8px}"
        ".cta-outline{display:inline-block;background:#fff;color:#0b6e86;border:2px solid #0b7d91;font-weight:800;padding:11px 20px;border-radius:28px;text-decoration:none}"
        ".hero-visual{margin:0}.hero-visual img{width:100%;height:auto;border-radius:18px;box-shadow:0 12px 32px rgba(23,56,74,.18);border:1px solid #cfe5ea}"
        ".map-legend{display:flex;gap:14px;justify-content:center;margin-top:8px;font-size:13px;color:#5a7684}"
        ".map-legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}"
        ".stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:22px 0;padding:18px;background:#0b6e86;color:#fff;border-radius:16px;text-align:center}"
        ".stats b{display:block;font-size:30px;line-height:1.1}.stats span{font-size:13px;opacity:.9}"
        ".how{margin:28px 0}.how h2{margin-top:0}.how-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:0;list-style:none;margin:14px 0 0}"
        ".how-grid li{background:#fff;border:1px solid #cfe5ea;border-radius:16px;padding:18px}"
        ".how-grid .n{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:#ffe9a8;color:#5a4500;font-weight:800;margin-bottom:8px}"
        ".how-grid b{display:block;font-size:17px;margin-bottom:4px}"
        ".teasers{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:28px 0}"
        ".teasers a{display:block;padding:22px;border-radius:16px;text-decoration:none;color:inherit;border:1px solid #cfe5ea;background:#fff}"
        ".teasers a.shop{background:#e6fbfc}.teasers a.mfg{background:#17384a;color:#fff;border-color:#17384a}"
        ".teasers a.mfg .muted{color:#9fe7f0}.teasers strong{display:block;font-size:20px;margin-bottom:6px}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;padding:0;list-style:none}"
        ".grid li a{display:block;padding:10px 12px;border:1px solid #cfe5ea;border-radius:12px;text-decoration:none;font-weight:700;background:#fff}"
        ".grid li a small{display:block;font-weight:400;color:#5a7684}.towns{font-size:15px}"
        ".band{padding:22px;border-radius:16px;margin:26px 0}.app{background:linear-gradient(135deg,#0b7d91,#0b6e86);color:#fff}.app .cta{background:#fff;color:#0b6e86}"
        "@media(max-width:860px){.hero{grid-template-columns:1fr}.hero h1{font-size:32px}.how-grid,.teasers,.stats{grid-template-columns:1fr 1fr}}"
        "@media(max-width:600px){.hero h1{font-size:28px}.stats,.how-grid,.teasers{grid-template-columns:1fr}.stats b{font-size:24px}}")


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
    L = lsv_limits()
    faq = [(q, a % {"n": n, "s": ns, "lsv": lsv_line(L)} if "%(" in a else a) for q, a in FAQ]
    title = f"Golf Cart Maps: golf cart map for {n} towns | LSV Map"
    desc = f"Golf Cart Maps: golf cart map and LSV map app for {n} beach and golf towns, with the law behind each rule." + POS.LANDING_DESC_TAIL
    cta = lambda pos: f'<a class="cta" href="/map" target="_blank" rel="noopener" data-ev="cta_try_map_click" data-p=\'{{"position":"{pos}"}}\'>Open the map</a>'
    k = lambda x: f"{x:,}"
    grid = "".join(f'<li><a href="/{r["slug"]}" data-ev="region_link_click" data-p=\'{{"region":"{e(r["id"])}"}}\'>{e(r["name"])}<small>{e(STATES.get(r["state"], r["state"]))}</small></a></li>' for r in sorted(regs, key=lambda r: (STATES.get(r["state"], r["state"]), r["name"])))
    tl = " · ".join(f'<a href="/{e(t["region"])}/{e(t["slug"])}">{e(t["name"])} golf cart rules</a>' for t in sorted(towns, key=lambda t: t["name"]))
    towns_json = json.dumps([{"name": r["name"], "slug": r["slug"], "id": r["id"], "state": STATES.get(r["state"], r["state"])} for r in sorted(regs, key=lambda r: r["name"])], ensure_ascii=False)
    body = f"""<section class="hero">
<div class="hero-copy">
<span class="pill">Free map · {n} beach &amp; golf towns · iPhone + CarPlay</span>
<h1>Know which roads your golf cart can legally ride.</h1>
<p class="sub">Green means go, red means skip. Pick your town, hop in the cart, and cruise the roads your city actually allows.</p>
<form class="find" id="townFind" action="/map" method="get" role="search">
<input type="search" id="townQ" name="q" placeholder="Find your town (Port Aransas, 30A, The Villages…)" autocomplete="off" aria-label="Find your town" aria-autocomplete="list" aria-controls="townList">
<button type="submit">Find map</button>
<ul class="find-list" id="townList" role="listbox" hidden></ul>
</form>
<div class="hero-actions">{cta("hero")}
<a class="cta-outline" href="{APPSTORE}" data-ev="app_store_click" data-p='{{"position":"hero_outline"}}'>Get it on iPhone</a></div>
<p><a class="appstore" href="{APPSTORE}" data-ev="app_store_click" data-p='{{"position":"hero"}}'><img src="/download-on-the-app-store.svg" width="143" height="48" alt="Download on the App Store"></a></p>
<p class="muted">Works in any browser. App Store live with Apple CarPlay.</p>
<p><label><input type="checkbox" id="remember"> Always open the map when I visit</label></p>
<p><a href="/golf-cart-maps">Golf cart maps by town</a> · <a href="/lsv">LSV map app</a></p>
</div>
<figure class="hero-visual">
<img src="/hero-map.jpg" width="900" height="506" alt="Golf cart map from Golf Cart Maps: legal golf cart and LSV roads in green, roads to avoid in red" loading="eager">
<figcaption class="map-legend"><span><i style="background:#12a150"></i>Legal cart roads</span><span><i style="background:#e5484d"></i>Avoid</span></figcaption>
</figure>
</section>
<div class="stats" role="list"><div role="listitem"><b>{k(st["road_mi"])}</b><span>road miles mapped</span></div><div role="listitem"><b>{n}</b><span>regions live</span></div><div role="listitem"><b>{ns}</b><span>states</span></div><div role="listitem"><b>{len(towns)}</b><span>town guides</span></div></div>
<section class="how" id="how">
<h2>How it works</h2>
<ol class="how-grid">
<li><span class="n">1</span><b>Pick your town</b>Search any of {n} beach and golf towns, from San Diego to The Villages.</li>
<li><span class="n">2</span><b>See green vs red</b>Legal golf cart and LSV roads light up green. Faster roads stay red.</li>
<li><span class="n">3</span><b>Ride with CarPlay</b>Take the same map on your iPhone and on your cart's dashboard screen.</li>
</ol>
</section>
<section class="teasers" aria-label="Partners">
<a class="shop" href="/for-rental-shops" data-ev="sales_click" data-p='{{"section":"home_teaser_shops"}}'><strong>For rental shops</strong><span>Hand every renter a free legal-roads map.</span><span class="muted"> Design partners get it at no cost.</span></a>
<a class="mfg" href="/for-manufacturers" data-ev="partner_click" data-p='{{"section":"home_teaser_mfg"}}'><strong>For manufacturers</strong><span>CarPlay maps as a dealer add-on.</span><span class="muted"> Talk with Max about a pilot.</span></a>
</section>
<!-- Trusted by: empty on purpose. Add partner names or logos only with that partner's written permission. -->
<section id="lsv"><h2>LSV map: roads posted 35 mph or less</h2>
<p>A street-legal golf cart is usually registered as an LSV (low speed vehicle): it has a VIN, plate and insurance and tops out at 25 mph. Pick LSV on the map and Golf Cart Maps becomes a low speed vehicle map, showing the roads an LSV may use in green: roads {e(lsv_line(L))}, unless a town or county bans LSVs from a road. Plain golf carts get their own, usually shorter, list.</p>
<p><a href="/lsv">LSV map app: low speed vehicle map</a></p></section>
<h2 id="regions">Where can I drive a golf cart?</h2>
<p>Live in {n} regions, from San Diego to The Villages, 30A, Hilton Head and Hawaii.</p>
<ul class="grid">{grid}</ul>
<h3>Town guides</h3><p class="towns">{tl}</p>
<section class="band app" id="iphone"><h2>iPhone app + CarPlay</h2>
<p>Take Golf Cart Maps on the road. The native iPhone app works with Apple CarPlay, so legal cart roads and turn-by-turn routes show up right on your car's dashboard screen.</p>
<p><a class="appstore" href="{APPSTORE}" data-ev="app_store_click" data-p='{{"position":"app_section"}}'><img src="/download-on-the-app-store.svg" width="161" height="54" alt="Download on the App Store"></a></p></section>
<h2>FAQ</h2>
{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in faq)}
<p>{cta("footer")}</p>"""
    ld = [org(), website(), software(), mobile_app(), faq_schema(faq)]
    head = ("<script>if(window.Capacitor||/^(capacitor|ionic):/.test(location.protocol))location.replace('map.html'+location.search);"
            "else if(location.hash.length>1){document.cookie='gcm_rd=hash; Max-Age=60; Path=/';location.replace('/map'+location.search+location.hash)}"
            "else{try{if(localStorage.getItem('gcm_skip_landing')==='1'&&!/[?&]stay=1/.test(location.search)){document.cookie='gcm_rd=cookie; Max-Age=60; Path=/';location.replace('/map'+location.search)}}catch(_){}}</script>")
    find_js = ("<script>(function(){var T=%s;var q=document.getElementById('townQ'),list=document.getElementById('townList'),form=document.getElementById('townFind');if(!q||!list||!form)return;"
               "function go(t){location.href='/map?r='+encodeURIComponent(t.id)}function show(items){list.innerHTML='';if(!items.length){list.hidden=true;list.style.display='none';return}"
               "items.slice(0,8).forEach(function(t){var li=document.createElement('li');var b=document.createElement('button');b.type='button';b.setAttribute('role','option');"
               "b.textContent=t.name+' ('+t.state+')';b.onclick=function(){go(t)};li.appendChild(b);list.appendChild(li)});list.hidden=false;list.style.display='block'}"
               "q.addEventListener('input',function(){var v=q.value.trim().toLowerCase();if(v.length<1){show([]);return}"
               "show(T.filter(function(t){return t.name.toLowerCase().indexOf(v)>=0||t.slug.indexOf(v)>=0||t.state.toLowerCase().indexOf(v)>=0}))});"
               "form.addEventListener('submit',function(ev){ev.preventDefault();var v=q.value.trim().toLowerCase();var hit=T.find(function(t){return t.name.toLowerCase()===v||t.slug===v})"
               "||T.find(function(t){return t.name.toLowerCase().indexOf(v)>=0||t.slug.indexOf(v)>=0});if(hit)go(hit);else location.href='/golf-cart-maps'});"
               "document.addEventListener('click',function(ev){if(!form.contains(ev.target)){list.hidden=true;list.style.display='none'}})})();</script>") % towns_json
    tail = ("<script>addEventListener('load',function(){var T=window.GCMTrack,c=document.getElementById('remember');try{c.checked=localStorage.getItem('gcm_skip_landing')==='1'}catch(_){}"
            "T&&T.track('landing_view',{});c.onchange=function(){try{if(c.checked){localStorage.setItem('gcm_skip_landing','1');document.cookie='gcm_skip=1; Max-Age=31536000; Path=/; SameSite=Lax'}else{localStorage.removeItem('gcm_skip_landing');document.cookie='gcm_skip=; Max-Age=0; Path=/'}}catch(_){}T&&T.track('remember_map_toggle',{on:c.checked})};"
            "document.querySelectorAll('a.cta').forEach(function(a){a.addEventListener('click',function(){try{sessionStorage.setItem('gcm_from_landing','1')}catch(_){}})})})</script>")
    return page(title, desc, "/", body, ld, head + "<style>" + LCSS + "</style>").replace("</body>", find_js + tail + '<script defer src="/hubspot.js"></script></body>')

if __name__ == "__main__":
    print(render()[:300])
