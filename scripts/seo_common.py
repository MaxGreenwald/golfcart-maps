"""Shared bits for the static SEO pages (region, town, compare, landing). Plain HTML, no map JS.
Product name on these pages: "Golf Cart Maps" (Max, Oct 19). Never "beta" (Max Oct 22: say "Free to use"), never "verified", no CarPlay/Android claims."""
import html, json, os, re, subprocess, datetime
import positioning as POS
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PUB = os.path.join(ROOT, "public")
SITE = "https://golfcartmap.com"
BRAND = "Golf Cart Maps"
LEGAL = "Golf Cart Maps LLC"
CONTACT = "max@golfcartmap.com"
SALES = "mailto:max@golfcartmap.com?subject=Golf%20Cart%20Maps%20sales%20inquiry"
TESTFLIGHT = "https://testflight.apple.com/join/P7dVC4zh"  # Max Oct 22: shown as the App Store badge; never say the word on the page
APPSTORE = "https://apps.apple.com/us/app/golf-cart-maps/id0000000000"  # placeholder: set once the App Store listing is live
STATES = {"CA":"California","FL":"Florida","GA":"Georgia","SC":"South Carolina","TX":"Texas","AL":"Alabama","AZ":"Arizona","OH":"Ohio","NC":"North Carolina","HI":"Hawaii","ME":"Maine"}
BANNED = re.compile(r"(?i)\bbeta\b|verified|android")  # guard-change: free allowed (Max Oct 22), beta banned
e = lambda s: html.escape(str(s), quote=True)

def today():
    return os.environ.get("SEO_DATE") or datetime.date.today().isoformat()

def month(d=None):
    d = datetime.date.fromisoformat(d or today()); return d.strftime("%b %Y")

def regions():
    return [r for r in json.load(open(os.path.join(PUB, "data", "regions.json"))) if not r.get("hidden")]

def rules():
    return json.load(open(os.path.join(PUB, "data", "rules.json")))

def effective_rules():
    """{region_id: {lsv: rule, golf_cart: rule}} computed by public/roadrule.js itself, so page text matches the map."""
    js = ("const R=require(%s);const rules=require(%s),regs=require(%s);const o={};"
          "for(const g of regs)o[g.id]={lsv:R.ruleFor(rules,g,'lsv'),golf_cart:R.ruleFor(rules,g,'golf_cart')};"
          "process.stdout.write(JSON.stringify(o))") % tuple(json.dumps(os.path.join(PUB, p)) for p in ("roadrule.js", "data/rules.json", "data/regions.json"))
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)

def org():
    return {"@context":"https://schema.org","@type":"Organization","@id":SITE+"/#org","name":BRAND,"legalName":LEGAL,"url":SITE+"/","logo":SITE+"/icon-512.png","email":CONTACT,"contactPoint":{"@type":"ContactPoint","contactType":"sales","email":CONTACT,"areaServed":"US","availableLanguage":"en"}}

def website():
    return {"@context":"https://schema.org","@type":"WebSite","@id":SITE+"/#website","name":BRAND,"url":SITE+"/","publisher":{"@id":SITE+"/#org"}}

def software():  # no offers block
    return {"@context":"https://schema.org","@type":"SoftwareApplication","name":BRAND,"applicationCategory":"NavigationApplication","operatingSystem":"iOS, Web","url":SITE+"/","publisher":{"@id":SITE+"/#org"}}

def mobile_app():  # the iPhone app (CarPlay built in); no ratings until real App Store ratings exist
    return {"@context":"https://schema.org","@type":"MobileApplication","name":BRAND,"operatingSystem":"iOS","applicationCategory":"NavigationApplication",
            "description":"Golf cart and LSV legal-road map and routes for iPhone, with Apple CarPlay on your car's dashboard screen.",
            "installUrl":TESTFLIGHT,"url":SITE+"/#iphone","offers":{"@type":"Offer","price":"0","priceCurrency":"USD"},"publisher":{"@id":SITE+"/#org"}}

def faq_schema(faq):
    return {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q, a in faq]}

def crumbs(items):
    return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":i+1,"name":n,"item":SITE+u} for i,(n,u) in enumerate(items)]}

CSS = ("body{margin:0;font:17px/1.55 -apple-system,system-ui,Segoe UI,Roboto,sans-serif;color:#17384a;background:#fbfdfd}"
       "header,main,footer{max-width:820px;margin:0 auto;padding:16px 20px}header{display:flex;gap:16px;align-items:center;flex-wrap:wrap}"
       "header a.home{font-weight:800;color:#0b6e86;text-decoration:none;font-size:19px}nav a{margin-right:14px;color:#0b6e86}"
       "h1{font-size:30px;line-height:1.2;margin:.4em 0}h2{margin-top:1.6em}a{color:#0b6e86}"
       ".cta{display:inline-block;background:#0b7d91;color:#fff;font-weight:800;padding:13px 22px;border-radius:28px;text-decoration:none;margin:8px 0}"
       "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #dde9ec;padding:8px;text-align:left;vertical-align:top}"
       ".muted{color:#5a7684;font-size:14px}footer{border-top:1px solid #dde9ec;margin-top:40px}ul.cols{columns:2}")

def page(title, desc, path, body, ld, extra_head=""):
    for t in (title, desc, body, json.dumps(ld)):
        m = BANNED.search(re.sub(r"<[^>]+>", " ", t))
        if m: raise SystemExit(f"banned word {m.group(0)!r} in page {path}")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE}{path}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{BRAND}"><meta property="og:url" content="{SITE}{path}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:image" content="{SITE}/og-v4.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="48x48"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#e8f7f8">{extra_head}
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head><body>
<header><a class="home" href="/">🏖️ {BRAND}</a><nav aria-label="Site"><a href="/#regions">Regions</a><a href="/#iphone">iPhone app</a><a href="/privacy">Privacy</a></nav></header>
<main>
{body}
</main>
<footer><p class="muted">{BRAND} (golfcartmap.com){POS.FOOTER_STATUS}. Not legal advice; posted signs and local law win. Updated {e(today())}. &copy; {LEGAL}. <a href="/privacy">Privacy</a> · Contact: <a href="mailto:{CONTACT}">{CONTACT}</a></p></footer>
<script defer src="/track.js"></script><script>addEventListener('load',function(){{var T=window.GCMTrack;if(!T)return;document.addEventListener('click',function(ev){{var a=ev.target.closest&&ev.target.closest('a[data-ev]');if(a)T.track(a.dataset.ev,JSON.parse(a.dataset.p||'{{}}'))}})}})</script>
</body></html>
"""
