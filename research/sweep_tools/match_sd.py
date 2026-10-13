import json, re, collections, math, pickle
from analyze import D, dist
from corridor import city
ents=[e for e in json.load(open('sd_entries.json')) if e['table'] in (1,2,3,4,7)]
AB={'av':'avenue','ave':'avenue','bl':'boulevard','blvd':'boulevard','st':'street','dr':'drive','rd':'road','py':'parkway','pkwy':'parkway','pl':'place','wy':'way','ct':'court','ln':'lane','hy':'highway','cr':'circle','cam':'camino','tr':'trail','n':'north','s':'south','w':'west','e':'east','mt':'mount'}
def norm(s):
    s=s.lower().replace('bi','bl') if re.search(r'\bbi\b|\bpi\b',s.lower()) else s.lower()
    s=re.sub(r'\bbi\b','bl',s); s=re.sub(r'\bpi\b','pl',s)
    s=re.sub(r'\b([a-z])st\b',r'\1 st',s) if re.match(r'^[a-z]st\b',s) else s
    s=re.sub(r'\(.*?\)','',s); s=re.sub(r'[^a-z0-9 ]',' ',s)
    s=re.sub(r'(\d+)(st|nd|rd|th)\b',r'\1',s)
    return exp(s.split())
def exp(t):
    out=[]
    for j,x in enumerate(t):
        if len(x)==1 and j+1<len(t) and t[j+1] in ('st','street','av','avenue') and j==0: out.append(x)
        else: out.append(AB.get(x,x))
    return ' '.join(out)
def onorm(s):
    s=s.lower(); s=re.sub(r'[^a-z0-9 ]',' ',s); s=re.sub(r'(\d+)(st|nd|rd|th)\b',r'\1',s)
    return exp(s.split())
byn=collections.defaultdict(list); nodenames=collections.defaultdict(set)
for i,d in enumerate(D):
    nm=d[1].get('name')
    if not nm: continue
    n=onorm(nm); 
    mid=d[2][len(d[2])//2]
    if city(mid[1],mid[0])!='San Diego': continue
    byn[n].append(i)
    for k,p in zip(d[3],d[2]): nodenames[k].add(n)
def xpos(ids,cross):
    c=norm(cross); c2=c.replace('north ','').replace('south ','').replace('west ','').replace('east ','')
    pts=[]
    for i in ids:
        for k,p in zip(D[i][3],D[i][2]):
            if any(n==c or n.endswith(' '+c) or n==c2 or n.replace('west ','').replace('east ','').replace('north ','').replace('south ','')==c2 for n in nodenames[k]): pts.append(p)
    if not pts:
        # fallback: geometric proximity to any way (any city) whose name matches the cross street (or a freeway ramp for SDxx)
        fw=re.match(r'sd ?(\d+)',c)
        cands=[j for j,d in enumerate(D) if (fw and d[1].get('highway','').startswith('motorway') and fw.group(1) in (d[1].get('ref','')+d[1].get('name',''))) or (d[1].get('name') and onorm(d[1]['name']).replace('west ','').replace('east ','').replace('north ','').replace('south ','')==c2)]
        cp=[p for j in cands for p in D[j][2]]
        if not cp: return None
        import bisect
        cp.sort(); best=None
        for i in ids:
            for p in D[i][2]:
                lo=bisect.bisect_left(cp,[p[0]-0.003])
                for q in cp[lo:]:
                    if q[0]>p[0]+0.003: break
                    if abs(q[1]-p[1])<0.003:
                        dd=dist(p,q)
                        if best is None or dd<best[0]: best=(dd,p)
        if best and best[0]<250: pts.append(best[1])
    if not pts: return None
    return (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts))
res=[]
for e in ents:
    n=norm(e['street']); ids=byn.get(n) or byn.get('west '+n) or byn.get('east '+n) or byn.get('north '+n) or byn.get('south '+n)
    if not ids: res.append((e,'no road',[])); continue
    a,b=xpos(ids,e['frm']),xpos(ids,e['to'])
    if not a or not b: res.append((e,'cross not found: '+(e['frm'] if not a else e['to']),[i for i in ids if D[i][4][0]>=40])); continue
    # select ways whose midpoint projects between a and b and lies within 120m of segment line
    ax,ay=a; bx,by=b; kx=93450; ky=110540
    vx,vy=(bx-ax)*kx,(by-ay)*ky; L=vx*vx+vy*vy
    if L<100: res.append((e,'zero length',[])); continue
    sel=[]
    for i in ids:
        g=D[i][2]; m=g[len(g)//2]; px,py=(m[0]-ax)*kx,(m[1]-ay)*ky
        u=(px*vx+py*vy)/L; dd=abs(px*vy-py*vx)/math.sqrt(L)
        if -0.01<=u<=1.01 and dd<400: sel.append(i)
    res.append((e,'ok',sel))
pickle.dump(res,open('sd_match.pkl','wb'))
ok=sum(1 for r in res if r[1]=='ok'); print('entries',len(res),'matched',ok)
for e,st,sel in res:
    red=[i for i in sel if D[i][4][0]>=40] if st=='ok' else sel
    if red: print(e['table'],e['mph'],e['street'],'(',e['frm'],'-',e['to'],')',e['dir'],st,'red',len(red),'of',len(sel),dict(collections.Counter((D[i][1].get('maxspeed'),D[i][4][1],D[i][4][0]) for i in red)))
print('---unmatched');[print(e['street'],e['frm'],e['to'],st) for e,st,s in res if st!='ok']
