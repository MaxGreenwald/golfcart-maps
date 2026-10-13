import pickle, math, collections, json
from analyze import D, comps, spots, dist, HWX
def city(lat,lon):
    if lat>33.205 or (lat>33.18 and lon<-117.33): return 'Oceanside'
    if lat>33.09: return 'Carlsbad' if lat<33.205 else 'Oceanside'
    if lat>33.0: return 'Encinitas'
    if lat>32.97 and lon<-117.245: return 'Solana Beach'
    if 32.94<lat<=32.982 and lon<-117.25: return 'Del Mar'
    if 32.66<lat<32.70 and -117.20<lon<-117.15 : return 'Coronado'
    if lat<32.6 and lon<-117.09: return 'Imperial Beach'
    if 32.645<lat<32.70 and lon>-117.125: return 'National City'
    if lat<32.645 and lon>-117.09: return 'Chula Vista'
    return 'San Diego'
runs=[]
for nm,ids in comps:
    red=[i for i in ids if D[i][4][0]>=40 and D[i][1].get('highway') not in HWX]
    if not red: continue
    allsig=[s for i in red for s in D[i][5]]
    if sum(1 for s in allsig if s['mph']<=35)<3: continue
    pts=[p for i in red for p in D[i][2]]
    la=max(p[1] for p in pts)-min(p[1] for p in pts); lo=(max(p[0] for p in pts)-min(p[0] for p in pts))*0.84
    ax=1 if la>=lo else 0
    sp=spots(allsig)
    # a spot is "low" if all its signs <=35, "high" if any >=40
    sp=[(sum((s['lon'],s['lat'])[ax] for s in c)/len(c), all(s['mph']<=35 for s in c), c) for c in sp]
    sp.sort(key=lambda x:x[0])
    cur=[]
    def flush():
        if len(cur)>=3:
            a,b=cur[0][0],cur[-1][0]; pad=0.0008
            la=[s['lat'] for x in cur for s in x[2]]; lo_=[s['lon'] for x in cur for s in x[2]]
            bb=(min(la)-pad,min(lo_)-pad,max(la)+pad,max(lo_)+pad)
            def inb(p): return bb[0]<=p[1]<=bb[2] and bb[1]<=p[0]<=bb[3]
            sel=[i for i in red if inb(D[i][2][len(D[i][2])//2]) and not any(s['mph']>=40 for s in D[i][5])]
            sig=[s for x in cur for s in x[2]]
            runs.append(dict(bb=bb,name=nm,ax='lat' if ax else 'lon',lo=a,hi=b,spots=len(cur),signs=len(sig),mph=max(s['mph'] for s in sig),
               speeds=sorted(collections.Counter(s['mph'] for s in sig).items()),ways=sel,
               osm=dict(collections.Counter(D[i][1].get('maxspeed') for i in sel)),src=dict(collections.Counter(D[i][4][1] for i in sel)),
               spotlist=[(round(x[2][0]['lat'],5),round(x[2][0]['lon'],5),x[2][0]['mph'],x[2][0]['id']) for x in cur],
               city=city(*[(x[2][0]['lat'],x[2][0]['lon']) for x in cur][len(cur)//2])))
    for x in sp:
        if x[1]: cur.append(x)
        else: flush(); cur=[]
    flush()
pickle.dump(runs,open('runs.pkl','wb'))
for r in runs: print(f"{r['name']:28} {r['city']:14} {r['ax']} {r['lo']:.4f}-{r['hi']:.4f} spots={r['spots']} mph<= {r['mph']} {r['speeds']} ways={len(r['ways'])} osm={r['osm']} src={r['src']}")
print(len(runs), sum(len(r['ways']) for r in runs))
