"""Routing regression: Max's La Jolla pair + ~30 random residential pairs (0.5-3 km apart)."""
from playwright.sync_api import sync_playwright
import os
URL=os.environ.get("URL","http://localhost:8765/")
import json,random,glob,math,os,sys
random.seed(int(sys.argv[1]) if len(sys.argv)>1 else 7)
segs=[]
for f in glob.glob(os.path.join(os.path.dirname(__file__),'..','public','data','sd','tiles','*.json')):
    segs+= [s for s in json.load(open(f)) if s[1]=='residential' and len(s[7])>=2 and (not os.environ.get('COAST') or s[7][0][0]<-117.22)]
def mid(s):p=s[7][len(s[7])//2];return [p[1],p[0]]
pairs=[("max_lajolla",[32.8461,-117.2786],[32.8434,-117.2776])]
while len(pairs)<31:
    a=mid(random.choice(segs));b=mid(random.choice(segs))
    d=math.hypot((a[0]-b[0])*111,(a[1]-b[1])*93)
    if 0.5<d<3: pairs.append((f"rand{len(pairs)}",a,b))
url=os.environ.get("URL",URL)
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page();pg.goto(url);pg.wait_for_function("window.ready===true",timeout=120000)
    if os.environ.get("LENIENT"): pg.evaluate("window.LENIENT=true;adj={};nodes={};buildGraph(0)")
    ok=0
    for n,a,c in pairs:
        r=pg.evaluate(f"testRoute({a},{c})");ok+=bool(r)
        print(n,a,c,r)
    print(f"SUCCESS {ok}/{len(pairs)} = {ok/len(pairs):.0%}");b.close()
