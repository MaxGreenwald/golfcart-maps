import re, math, collections, bisect
from analyze import D, dist
AB={'av':'avenue','ave':'avenue','bl':'boulevard','blvd':'boulevard','st':'street','dr':'drive','rd':'road','py':'parkway','pkwy':'parkway','pl':'place','wy':'way','ct':'court','ln':'lane','hy':'highway','hwy':'highway','cr':'circle','n':'north','s':'south','w':'west','e':'east','mt':'mount'}
def exp(t):
    return ' '.join(x if (len(x)==1 and j==0 and j+1<len(t) and t[j+1] in ('st','street','av','avenue')) else AB.get(x,x) for j,x in enumerate(t))
def norm(s):
    s=s.lower(); s=re.sub(r"[^a-z0-9 ]",' ',s); s=re.sub(r'(\d+)(st|nd|rd|th)\b',r'\1',s)
    return exp(s.split())
def strip(n): return re.sub(r'^(north|south|east|west) ','',n)
CITYBOX={'Encinitas':(32.99,-117.32,33.095,-117.17),'Oceanside':(33.165,-117.42,33.30,-117.24),'Imperial Beach':(32.555,-117.14,32.595,-117.09)}
ALIAS={'coast highway 101':['north coast highway 101','south coast highway 101','coast highway 101','north coast highway','south coast highway','coast highway','north highway 101','south highway 101','highway 101'],
       'state route 75':['palm avenue','silver strand boulevard','state route 75'],'strand':['the strand','north the strand','south the strand','strand','the strand north','the strand south','north strand','south strand']}
def inb(p,b): return b[0]<=p[1]<=b[2] and b[1]<=p[0]<=b[3]
class M:
    def __init__(s,city):
        s.box=CITYBOX[city]; s.byn=collections.defaultdict(list); s.nn=collections.defaultdict(set)
        for i,d in enumerate(D):
            nm=d[1].get('name')
            if not nm or not inb(d[2][len(d[2])//2],s.box): continue
            n=norm(nm); s.byn[n].append(i)
            for k in d[3]: s.nn[k].add(n)
    def road(s,name):
        n=norm(name); keys=set([n]); 
        for a,v in ALIAS.items():
            if strip(n)==strip(a) or n==a or n in v: keys|=set(v)
        keys|={'north '+strip(n),'south '+strip(n),'east '+strip(n),'west '+strip(n),strip(n)}
        return [i for k in keys for i in s.byn.get(k,[])]
    def cross(s,ids,c):
        c0=c; cl=c.lower()
        if re.search(r'limit|end\b',cl): return None
        fw=re.search(r'\bi ?-? ?(\d+)\b|interstate (\d+)|state route (\d+)|highway (76|78)\b',cl)
        if cl.startswith('state route 75') or cl=='sr-75': fw=None; c='palm avenue'
        if fw and 'coast' not in cl:
            num=[g for g in fw.groups() if g][0]
            cands=[j for j,d in enumerate(D) if d[1].get('highway','').startswith('motorway') and re.search(r'\b'+num+r'\b',d[1].get('ref',''))]
        else:
            cn=strip(norm(c)); cn2=cn.replace(' road',' drive') if cn.endswith(' road') else cn
            if "swami" in cn: return 'SWAMIS'
            cands=[j for j,d in enumerate(D) if d[1].get('name') and strip(norm(d[1]['name'])) in (cn,cn2) or (cn=='coast highway 101' and d[1].get('name') and 'Coast Highway' in d[1]['name'])]
        cp=sorted(p for j in cands for p in D[j][2] if inb(p,(s.box[0]-.02,s.box[1]-.02,s.box[2]+.02,s.box[3]+.02)))
        if not cp: return None
        best=None
        for i in ids:
            for p in D[i][2]:
                lo=bisect.bisect_left(cp,[p[0]-0.003])
                for q in cp[lo:]:
                    if q[0]>p[0]+0.003: break
                    if abs(q[1]-p[1])<0.003:
                        dd=dist(p,q)
                        if best is None or dd<best[0]: best=(dd,p)
        return best[1] if best and best[0]<250 else None
    def seg(s,name,a,b):
        ids=s.road(name)
        if not ids: return 'no road',[]
        pa,pb=s.cross(ids,a),s.cross(ids,b)
        if pa=='SWAMIS': pa=(-117.2925,33.0345)
        if pb=='SWAMIS': pb=(-117.2925,33.0345)
        pts=[(i,D[i][2][len(D[i][2])//2]) for i in ids]
        def openend(c,other):
            cl=c.lower()
            if 'north' in cl: key=lambda p:p[1]
            elif 'south' in cl: key=lambda p:-p[1]
            elif 'east' in cl: key=lambda p:p[0]
            elif 'west' in cl: key=lambda p:-p[0]
            else: return None
            # farthest point along that direction among road ways connected-ish (within city box)
            return max((p for _,p in pts), key=key)
        if pa is None and pb is not None: pa=openend(a,pb)
        if pb is None and pa is not None: pb=openend(b,pa)
        if pa is None or pb is None: return 'cross not found: '+(a if pa is None else b), ids
        kx,ky=93450,110540; vx,vy=(pb[0]-pa[0])*kx,(pb[1]-pa[1])*ky; L=vx*vx+vy*vy
        if L<400: return 'zero length',[]
        sel=[]
        for i,m in pts:
            px,py=(m[0]-pa[0])*kx,(m[1]-pa[1])*ky; u=(px*vx+py*vy)/L; dd=abs(px*vy-py*vx)/math.sqrt(L)
            if -0.005<=u<=1.005 and dd<300: sel.append(i)
        return 'ok',sel
