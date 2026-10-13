import re, json
pages=open('r.txt').read().split('\f')
def table(pg):
    if 9<=pg<=15: return 1
    if 16<=pg<=18: return 2
    if pg==19: return 3
    if pg in (20,21): return 4
    if 22<=pg<=47: return 5
    if 48<=pg<=153: return 6
    if pg==154: return 7
ents=[]
for i,p in enumerate(pages,start=1):
    t=table(i)
    if not t: continue
    txt=re.sub(r'\n\s*(?=[a-z])','',p)  # join OCR-split words
    for l in txt.splitlines():
        m=re.match(r'\s*(.+?)\s*\((.+?)\s+-\s*(.+?)\)\s*(?:supersedes\S*\s*)?(.*?)$',l)
        if not m: m=re.match(r'\s*(.+?)\s*\((.+?)\s*-\s+(.+?)\)\s*(.*?)$',l)
        if not m: continue
        rest=m.group(4); sp=re.search(r'(\d{2})\s*$',rest)
        d=re.sub(r'\s','',rest).lower()
        dr='NB' if 'north' in d else 'SB' if 'south' in d else 'EB' if 'east' in d else 'WB' if 'west' in d else 'Both'
        mph={1:'-5',2:'-5',3:'25',4:'25'}.get(t, sp.group(1) if sp else None)
        ents.append(dict(table=t,page=i,street=m.group(1).strip(),frm=m.group(2).strip(),to=m.group(3).strip(),dir=dr,mph=mph))
json.dump(ents,open('sd_entries.json','w'),indent=0)
import collections; print(collections.Counter(e['table'] for e in ents))
for e in ents:
    if e['table'] in (1,2,3,4,7): pass
print([e for e in ents if e['table']==7])
