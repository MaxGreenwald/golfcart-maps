"""WebKit (Safari engine) layout test for the region chip, with iOS-style <select> padding injected.
Why: on iPhone, WebKit adds its own inner padding to native <select> controls, which truncated the region
name with "..." (build 8, Oct 17). Desktop/Linux engines don't add it, so we simulate it here.
Asserts for every visible region at 375/390/430 px: no chip text overflows (scrollWidth > clientWidth,
or a <select> showing its text narrower than the text), chips don't overlap or run off-screen.
Run: URL=http://localhost:8765/ python3 scripts/test_chip_overflow.py   (exit 1 on failure)"""
import json, os, sys
from playwright.sync_api import sync_playwright
U = os.environ.get("URL", "http://localhost:8765/").rstrip("/")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REGS = [r["id"] for r in json.load(open(os.path.join(ROOT, "public/data/regions.json"))) if not r.get("hidden")]
IOS_SELECT = "select{padding-left:10px!important;padding-right:24px!important}"   # ~ what iOS WebKit adds around menulist text
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
JS = """()=>{const C=document.querySelector('#chips');const els=[...C.querySelectorAll('*')].filter(e=>e.offsetParent&&e.tagName!=='OPTION');const bad=[];
for(const e of els){const cs=getComputedStyle(e);if(cs.opacity==='0')continue;
 if(e.tagName==='SELECT'){const cx=document.createElement('canvas').getContext('2d');cx.font=cs.font;const t=e.selectedOptions[0]?e.selectedOptions[0].text:'';
  const need=cx.measureText(t).width+parseFloat(cs.paddingLeft)+parseFloat(cs.paddingRight);if(need>e.clientWidth+0.5)bad.push('select text "'+t+'" needs '+Math.round(need)+'px, has '+e.clientWidth)}
 else if(e.children.length===0&&e.textContent.trim()&&e.scrollWidth>e.clientWidth+0.5&&cs.display!=='inline')bad.push('"'+e.textContent.trim()+'" scrollWidth '+e.scrollWidth+' > '+e.clientWidth);
 if(cs.textOverflow==='ellipsis'&&e.scrollWidth>e.clientWidth+0.5)bad.push('ellipsis on '+(e.id||e.className))}
const ch=[...C.children].filter(e=>e.offsetParent),R=ch.map(e=>e.getBoundingClientRect());
for(let i=0;i<R.length;i++){if(R[i].right>innerWidth-2)bad.push((ch[i].id||ch[i].className)+' off-screen');for(let j=i+1;j<R.length;j++){const a=R[i],b=R[j];if(a.left<b.right-1&&b.left<a.right-1&&a.top<b.bottom-1&&b.top<a.bottom-1)bad.push('overlap '+(ch[i].id||ch[i].className)+' / '+(ch[j].id||ch[j].className))}}
const lbl=document.querySelector('#cityLbl'),sel=document.querySelector('#city');const shown=lbl?lbl.textContent:(sel.selectedOptions[0]||{}).text;
return {bad,shown}}"""
fails = 0
with sync_playwright() as p:
    b = p.webkit.launch()
    for w, h in ((375, 667), (390, 844), (430, 932)):
        c = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True, user_agent=UA)
        for rid in REGS:
            pg = c.new_page(); pg.goto(f"{U}/?r={rid}"); pg.wait_for_function("window.ready===true&&window.REG", timeout=90000)
            pg.add_style_tag(content=IOS_SELECT); pg.evaluate("document.fonts.ready.then(()=>1)"); pg.wait_for_timeout(400)
            r = pg.evaluate(JS); ok = not r["bad"]; fails += not ok
            print("PASS" if ok else "FAIL", w, rid, repr(r["shown"]), "; ".join(r["bad"]))
            pg.close()
        c.close()
    b.close()
print("RESULT", "ALL PASS" if not fails else f"{fails} FAIL"); sys.exit(1 if fails else 0)
