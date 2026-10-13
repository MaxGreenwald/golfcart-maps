import pickle, json, collections, re
from analyze import D
runs=pickle.load(open('runs.pkl','rb')); sd=pickle.load(open('sd_match.pkl','rb')); cr=pickle.load(open('city_res.pkl','rb'))
SD_URL="https://docs.sandiego.gov/council_reso_ordinance/rao2026/R-316675.pdf"
TBL={1:'Table 1 safety corridor, -5 mph',2:'Table 2 ped/bike corridor, -5 mph',3:'Table 3 business district, 25 mph',4:'Table 4 business district, 25 mph',7:'Table 7, posted'}
HWX=('motorway','motorway_link','trunk','trunk_link')
ways={}; changes=[]  # changes: (group key, way idx, old, new)
def key(i): d=D[i]; return f"{d[1].get('name','')}|{d[3][0]}|{d[3][-1]}"
def setw(i,mph,url,label,group):
    if D[i][4][1]=='verified' or D[i][1].get('highway') in HWX: return
    k=key(i)
    if k in ways: return
    old=D[i][4][0]
    if (old>=40)==(mph>=40): return  # status unchanged: skip (keep diff minimal)
    ways[k]={"mph":mph,"url":url,"label":label}; changes.append((group,i,old,mph))
# A) San Diego R-316675
for e,st,sel in sd:
    if st!='ok': continue
    t=e['table']; seg=f"{e['street']} ({e['frm']} - {e['to']})".replace(' BI',' Bl').replace(' PI',' Pl')
    if t in (3,4,7):
        mph=int(e['mph'])
        for i in sel:
            if D[i][4][0]>=40: setw(i,mph,SD_URL,f"San Diego R-316675 {TBL[t]}: {seg}",('San Diego',seg,f"R-316675 {TBL[t]}"))
    elif t in (1,2):
        for i in sel:
            if D[i][4][0]==40: setw(i,35,SD_URL,f"San Diego R-316675 {TBL[t]} (posted 40 -> 35): {seg}",('San Diego',seg,f"R-316675 {TBL[t]}; existing 40 (OSM/Mapillary)"))
MAN=[("Broadway",(32.714,-117.1557,32.717,-117.1476),25,4,"Broadway (Park Bl - 17th St)"),
     ("India Street",(32.7152,-117.1715,32.7322,-117.1665),25,4,"India St (W Kalmia St - Broadway)"),
     ("Market Street",(32.710,-117.1682,32.712,-117.1623),25,4,"Market St (Columbia St - 3rd Av)"),
     ("West Hawthorn Street",(32.730,-117.1737,32.7325,-117.1663),25,3,"W Hawthorn St (N Harbor Dr - SD 5)"),
     ("G Street",(32.7125,-117.1727,32.7145,-117.1476),25,4,"G St (Pacific Hy - 17th St)"),
     ("J Street",(32.7083,-117.1627,32.7106,-117.1476),25,4,"J St (2nd Av - 17th St)"),
     ("A Street",(32.718,-117.1662,32.7205,-117.1558),25,4,"A St (Front St - 9th Av)"),
     ("10th Avenue",(32.708,-117.1572,32.7200,-117.1548),25,4,"10th Av (Ash St - K St)")]
for nm,bb,mph,t,seg in MAN:
    for i,d in enumerate(D):
        if d[1].get('name')!=nm: continue
        m=d[2][len(d[2])//2]
        if bb[0]<=m[1]<=bb[2] and bb[1]<=m[0]<=bb[3] and d[4][0]>=40: setw(i,mph,SD_URL,f"San Diego R-316675 {TBL[t]}: {seg}",('San Diego',seg,f"R-316675 {TBL[t]}"))
for i,d in enumerate(D):
    if d[1].get('name')=='Washington Street' and d[4][0]==40:
        m=d[2][len(d[2])//2]
        if 32.745<=m[1]<=32.757 and -117.193<=m[0]<=-117.149: setw(i,35,SD_URL,"San Diego R-316675 Table 1 safety corridor (posted 40 -> 35): Washington St (Pacific Hy - Normal St)",('San Diego','Washington St (Pacific Hy - Normal St)','R-316675 Table 1; existing 40 (OSM)'))
# B-D) other cities
SKIP={('Encinitas','Rancho Santa Fe Rd'),('Encinitas','S Rancho Santa Fe Rd'),('Oceanside','Vista Way')}
for r in cr:
    if r['status']!='ok' or (r['city'],r['road']) in SKIP: continue
    seg=f"{r['road']} ({r['frm']} - {r['to']})"; lab=f"{r['cite']}: {seg} posted {r['mph']}"
    for i in r['sel']:
        m=D[i][2][len(D[i][2])//2]
        if r['road']=='La Costa Ave' and not (-117.3090<=m[0]<=-117.2968): continue  # 101 - I-5 only (east end ambiguous)
        if r['mph']<=35 and D[i][4][0]>=40: setw(i,r['mph'],r['url'],lab,(r['city'],seg,r['cite']))
        if r['mph']>=40 and D[i][4][0]<40 and r['road']=='El Camino Real' and 33.059<=m[1]<=33.083 and D[i][1].get('highway')=='primary':
            setw(i,r['mph'],r['url'],lab,(r['city'],seg,r['cite']))
# E) corridor rule
for r in runs:
    for i in r['ways']:
        sp=', '.join(f"{a},{b}" for a,b,_,_ in r['spotlist'][:3])
        s0=r['spotlist'][len(r['spotlist'])//2]
        url=f"https://www.mapillary.com/app/?lat={s0[0]}&lng={s0[1]}&z=19&focus=map&mapFeatureId={s0[3]}"
        setw(i,r['mph'],url,f"Mapillary corridor: {r['spots']} spots on {r['name']} with posted <= {r['mph']} signs ({r['speeds']})",(r['city'],f"{r['name']} {r['lo']:.4f}..{r['hi']:.4f} ({r['ax']})",f"Mapillary corridor rule: {r['spots']} spots, signs {r['speeds']}"))
json.dump({"generated":"2026-10-13","ways":ways},open('/workspace/golfcart-maps/research/accuracy_sweep.json','w'),indent=0,sort_keys=True)
pickle.dump(changes,open('changes.pkl','wb'))
g=collections.OrderedDict()
for grp,i,old,new in changes: g.setdefault(grp,[]).append((i,old,new))
for (city,seg,ev),L in g.items():
    pts=[D[i][2][len(D[i][2])//2] for i,_,_ in L]
    print(f"{city} | {seg} | {len(L)} ways | old {sorted(set(o for _,o,_ in L))} -> {sorted(set(n for _,_,n in L))} | {ev} | {min(p[1] for p in pts):.4f},{min(p[0] for p in pts):.4f}..{max(p[1] for p in pts):.4f},{max(p[0] for p in pts):.4f}")
print(len(ways),'ways', collections.Counter('allowed' if n<40 else 'forbidden' for _,_,_,n in changes))
