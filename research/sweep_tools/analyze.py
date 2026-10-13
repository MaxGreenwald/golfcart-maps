import pickle, math, json, collections
D=pickle.load(open('ways.pkl','rb'))
kx=111320*math.cos(math.radians(32.9)); ky=110540
def dist(a,b): return math.hypot((a[0]-b[0])*kx,(a[1]-b[1])*ky)
# components of same-name ways
byname=collections.defaultdict(list)
for i,d in enumerate(D):
    nm=d[1].get('name')
    if nm: byname[nm].append(i)
comps=[]
for nm,ids in byname.items():
    par={i:i for i in ids}
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    nodeown={}
    for i in ids:
        for n in (D[i][3][0],D[i][3][-1]):
            if n in nodeown: par[f(i)]=f(nodeown[n])
            else: nodeown[n]=i
    # also join endpoints within 60m (divided carriageways / gaps)
    ends=[(i,D[i][2][0]) for i in ids]+[(i,D[i][2][-1]) for i in ids]
    for a in range(len(ends)):
        for b in range(a+1,len(ends)):
            if f(ends[a][0])!=f(ends[b][0]) and dist(ends[a][1],ends[b][1])<60: par[f(ends[a][0])]=f(ends[b][0])
    g=collections.defaultdict(list)
    for i in ids: g[f(i)].append(i)
    comps+= [(nm,v) for v in g.values()]
def spots(signs):
    cl=[]
    for s in sorted(signs,key=lambda s:(s['lat'],s['lon'])):
        for c in cl:
            if dist((s['lon'],s['lat']),(c[0]['lon'],c[0]['lat']))<60: c.append(s); break
        else: cl.append([s])
    return cl
HWX=('motorway','motorway_link','trunk','trunk_link')
red3=[]; corridor=[]; reverse=[]
for nm,ids in comps:
    red=[i for i in ids if D[i][4][0]>=40 and D[i][1].get('highway') not in HWX]
    if red:
        low=[s for i in red for s in D[i][5] if s['mph']<=35]; high=[s for i in red for s in D[i][5] if s['mph']>=40]
        if low:
            ls=spots(low); hs=spots(high)
            pts=[p for i in red for p in D[i][2]]
            ent=dict(name=nm,ids=red,nred=len(red),low_signs=len(low),low_spots=len(ls),high_spots=len(hs),
                     speeds=sorted(collections.Counter(s['mph'] for s in low).items()),
                     spots=[(round(c[0]['lat'],5),round(c[0]['lon'],5),c[0]['mph'],len(c),c[0]['id']) for c in ls],
                     hspots=[(round(c[0]['lat'],5),round(c[0]['lon'],5),c[0]['mph'],len(c)) for c in hs],
                     bbox=(min(p[1] for p in pts),min(p[0] for p in pts),max(p[1] for p in pts),max(p[0] for p in pts)),
                     src=collections.Counter(D[i][4][1] for i in red), osm=collections.Counter(D[i][1].get('maxspeed') for i in red), hw=collections.Counter(D[i][1].get('highway') for i in red))
            red3.append(ent)
    ok=[i for i in ids if D[i][4][0]<40]
    if ok:
        hi=[s for i in ok for s in D[i][5] if s['mph']>=40]
        if hi:
            hs=spots(hi)
            reverse.append(dict(name=nm,ids=ok,hi_signs=len(hi),hi_spots=len(hs),spots=[(round(c[0]['lat'],5),round(c[0]['lon'],5),c[0]['mph'],len(c),c[0]['id']) for c in hs],src=collections.Counter(D[i][4][1] for i in ok if any(s['mph']>=40 for s in D[i][5])),shown=sorted(set(D[i][4][0] for i in ok if any(s['mph']>=40 for s in D[i][5])))))
red3.sort(key=lambda e:-e['low_spots'])
pickle.dump((red3,reverse),open('res.pkl','wb'))
if __name__=="__main__": print(len(red3),len(reverse))
if __name__=="__main__":
 for e in red3:
    print(f"{e['name']:32} spots={e['low_spots']} signs={e['low_signs']} hi_spots={e['high_spots']} {e['speeds']} bbox={tuple(round(x,3) for x in e['bbox'])} src={dict(e['src'])} osm={dict(e['osm'])} hw={dict(e['hw'])}")
