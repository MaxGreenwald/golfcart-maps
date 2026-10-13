import sys, os, json, math, pickle
os.chdir('/workspace/golfcart-maps'); sys.argv=['x']
src=open('scripts/build_data.py').read()
src=src.split('os.makedirs(os.path.join(os.path.dirname(__file__), "..", "research")')[0]
src=src.replace('    stats[src] += 1\n','    stats[src] += 1; FINAL[wi]=(s,src,si)\n')
src=src.replace('__file__','"scripts/build_data.py"')
import mapillary_signs_hook
g={'__name__':'h','FINAL':{}}
sys.path.insert(0,'scripts')
exec(compile(src,'build','exec'),g)
FINAL=g['FINAL']; wl=g['wl']; ov=g['ov']
per=mapillary_signs_hook.per_signs([(w["tags"], [[q["lon"], q["lat"]] for q in w["geometry"]]) for w in wl])
data=[(w['id'],w['tags'],[[q['lon'],q['lat']] for q in w['geometry']],w['nodes'],FINAL[i],per.get(i,[]), i in ov) for i,w in enumerate(wl)]
pickle.dump(data,open('/workspace/sweep/ways.pkl','wb'))
print(len(data))
