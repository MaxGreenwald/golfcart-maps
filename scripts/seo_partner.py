#!/usr/bin/env python3
"""Partner invite pages: /for-rental-shops and /for-manufacturers (Max via Gary, Nov 6 2026).
Design partners at no cost. No dollar prices, no booking links, no partner names, no portal promise."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import *

SHOP_MAIL = "mailto:max@golfcartmap.com?subject=Rental%20shop%3A%20get%20on%20the%20map"
MFG_MAIL = "mailto:max@golfcartmap.com?subject=Manufacturer%20%2F%20dealer%20pilot"
PCSS = (".steps{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0;padding:0;list-style:none}"
        ".steps li{background:#fff;border:1px solid #cfe5ea;border-radius:14px;padding:16px}"
        ".steps b{display:block;color:#0b6e86;font-size:13px;letter-spacing:.04em;text-transform:uppercase;margin-bottom:6px}"
        ".proof{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}"
        ".proof div{background:#0b6e86;color:#fff;border-radius:14px;padding:14px;text-align:center}"
        ".proof b{display:block;font-size:26px;line-height:1.1}"
        ".cta-row{margin:22px 0}"
        "@media(max-width:700px){.steps,.proof{grid-template-columns:1fr}}")


def _stats():
    import subprocess, json
    return json.loads(subprocess.run(
        ["node", os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_stats.js")],
        capture_output=True, text=True, check=True).stdout)


def shops_page():
    regs = regions()
    n, ns = len(regs), len({r["state"] for r in regs})
    st = _stats()
    title = "For rental shops | Golf Cart Maps"
    desc = ("Get your renters on the legal roads without a counter lecture. Design-partner shops get Golf Cart Maps "
            "at no cost while we shape the product with you.")
    body = f"""<nav aria-label="Breadcrumb" class="muted"><a href="/">Home</a> › For Rental Shops</nav>
<h1>Get your renters on the legal roads, without a counter lecture</h1>
<p>Golf Cart Maps shows which streets golf carts and LSVs may use in your town. Design-partner shops get it at no cost while we shape the product with you.</p>
<div class="cta-row"><a class="cta" href="{SHOP_MAIL}" data-ev="sales_click" data-p='{{"section":"rental_shops"}}'>Get your shop on the map</a></div>
<h2>Why shops care</h2>
<ul>
<li>Fewer "where can I drive?" questions at the counter.</li>
<li>Fewer guests ending up on 40+ mph roads.</li>
<li>A town map you can hand every renter.</li>
</ul>
<h2>What you get</h2>
<ul>
<li>Your town's live map on Golf Cart Maps.</li>
<li>A shop listing on the site.</li>
<li>QR stickers for each cart (we can supply).</li>
<li>Feedback calls on a handshake, nothing signed.</li>
</ul>
<h2>How it works</h2>
<ol class="steps">
<li><b>1. Join</b>Say you want in as a design partner. We get your town and shop details.</li>
<li><b>2. Stick a QR</b>Put a QR on each dash. Renters scan and open your town map.</li>
<li><b>3. Ride</b>Renters use the free map for your town. You get fewer wrong-road calls.</li>
</ol>
<h2>Coverage</h2>
<div class="proof" role="list">
<div role="listitem"><b>{st["road_mi"]:,}</b><span>road miles mapped</span></div>
<div role="listitem"><b>{n}</b><span>regions live</span></div>
<div role="listitem"><b>{ns}</b><span>states</span></div>
</div>
<div class="cta-row"><a class="cta" href="{SHOP_MAIL}" data-ev="sales_click" data-p='{{"section":"rental_shops_footer"}}'>Get your shop on the map</a>
<p class="muted">Or email <a href="mailto:{CONTACT}">{CONTACT}</a>. No prices on this page. Drivers keep using the map free.</p></div>"""
    webpage = {"@context": "https://schema.org", "@type": "WebPage", "name": title,
               "url": SITE + "/for-rental-shops", "isPartOf": {"@id": SITE + "/#website"}}
    ld = [org(), website(), webpage, crumbs([("Home", "/"), ("For Rental Shops", "/for-rental-shops")])]
    return page(title, desc, "/for-rental-shops", body, ld, "<style>" + PCSS + "</style>")


def manufacturers_page():
    regs = regions()
    n = len(regs)
    title = "For manufacturers and dealers | Golf Cart Maps"
    desc = ("Put legal-road maps on every cart that leaves the lot. Golf Cart Maps is a free iPhone + CarPlay app "
            f"covering {n} beach and golf towns. Talk with Max about a pilot.")
    body = f"""<nav aria-label="Breadcrumb" class="muted"><a href="/">Home</a> › For Manufacturers</nav>
<h1>Put legal-road maps on every cart that leaves the lot</h1>
<p>Golf Cart Maps is a free iPhone + CarPlay app covering {n} beach and golf towns. We partner with manufacturers and dealers on pilots that put the map in buyers' hands.</p>
<div class="cta-row"><a class="cta" href="{MFG_MAIL}" data-ev="partner_click" data-p='{{"section":"manufacturers"}}'>Talk with Max about a pilot</a></div>
<h2>The buyer problem</h2>
<p>New owners ask where they can drive. Local rules differ town by town. A clear map at purchase saves support calls and keeps riders on the legal roads.</p>
<h2>What we offer</h2>
<ul>
<li>CarPlay-ready map as a dealer add-on at purchase.</li>
<li>Co-branded or white-label pilot options.</li>
<li>Town-by-town rules with the law behind each one.</li>
</ul>
<h2>Proof without name-dropping</h2>
<ul>
<li>{n} regions live across beach and golf towns.</li>
<li>App Store listing live, free to download.</li>
<li>CarPlay on the dashboard screen.</li>
</ul>
<h2>How a pilot works</h2>
<ol class="steps">
<li><b>1. Intro call</b>Short call with Max about your markets and buyers.</li>
<li><b>2. Pick markets</b>Choose a dealer group or launch market to try first.</li>
<li><b>3. Decide together</b>Run the trial, review the results, then choose next steps.</li>
</ol>
<div class="cta-row"><a class="cta" href="{MFG_MAIL}" data-ev="partner_click" data-p='{{"section":"manufacturers_footer"}}'>Talk with Max about a pilot</a>
<p class="muted">Or email <a href="mailto:{CONTACT}">{CONTACT}</a>. No prices on this page.</p></div>"""
    webpage = {"@context": "https://schema.org", "@type": "WebPage", "name": title,
               "url": SITE + "/for-manufacturers", "isPartOf": {"@id": SITE + "/#website"}}
    ld = [org(), website(), webpage, crumbs([("Home", "/"), ("For Manufacturers", "/for-manufacturers")])]
    return page(title, desc, "/for-manufacturers", body, ld, "<style>" + PCSS + "</style>")


def build(out):
    open(os.path.join(out, "for-rental-shops.html"), "w", encoding="utf-8").write(shops_page())
    open(os.path.join(out, "for-manufacturers.html"), "w", encoding="utf-8").write(manufacturers_page())


if __name__ == "__main__":
    print("shops", len(shops_page()), "mfg", len(manufacturers_page()))
