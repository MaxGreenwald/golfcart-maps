import collections, pickle, lists
from match_gen import M, D
res=[]
for city,ents,url in [('Encinitas',lists.enc(),lists.ENC_URL),('Oceanside',lists.oc(),lists.OC_URL),('Imperial Beach',lists.ib(),lists.IB_URL)]:
    m=M(city)
    for road,a,b,mph,cite in ents:
        st,sel=m.seg(road,a,b)
        red=[i for i in sel if D[i][4][0]>=40]; ok=[i for i in sel if D[i][4][0]<40]
        res.append(dict(city=city,road=road,frm=a,to=b,mph=mph,cite=cite,url=url,status=st,sel=sel))
        flag=''
        if st=='ok' and mph<=35 and red: flag='FLIP->OK'
        if st=='ok' and mph>=40 and ok: flag='REVERSE'
        if flag or st!='ok':
            grp=red if flag=='FLIP->OK' else ok if flag=='REVERSE' else []
            print(f"{flag:9} {city:10} {road} ({a} - {b}) {mph} [{st}] n={len(grp)}/{len(sel)}",dict(collections.Counter((D[i][4][0],D[i][4][1],max([s['mph'] for s in D[i][5]],default=None)) for i in grp)))
pickle.dump(res,open('city_res.pkl','wb'))
