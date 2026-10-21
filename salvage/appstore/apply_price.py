import sys,json
sys.path.insert(0,'/workspace/ascapi')
from asc import call
APP='6823958385'
s,j=call('GET',f'/v1/apps/{APP}/appPricePoints?filter[territory]=USA&limit=5')
pp=[x for x in j['data'] if float(x['attributes']['customerPrice'])==0.0];print('price points',s,[(x['id'],x['attributes']) for x in pp][:1])
pid=pp[0]['id']
body={'data':{'type':'appPriceSchedules','relationships':{'app':{'data':{'type':'apps','id':APP}},'baseTerritory':{'data':{'type':'territories','id':'USA'}},'manualPrices':{'data':[{'type':'appPrices','id':'${p0}'}]}}},
 'included':[{'type':'appPrices','id':'${p0}','attributes':{'startDate':None},'relationships':{'appPricePoint':{'data':{'type':'appPricePoints','id':pid}}}}]}
s,j=call('POST','/v1/appPriceSchedules',body);print('price',s,json.dumps(j)[:500] if s>=300 else 'ok')
body={'data':{'type':'appAvailabilities','attributes':{'availableInNewTerritories':False},'relationships':{'app':{'data':{'type':'apps','id':APP}},'territoryAvailabilities':{'data':[{'type':'territoryAvailabilities','id':'${t0}'}]}}},
 'included':[{'type':'territoryAvailabilities','id':'${t0}','attributes':{'available':True},'relationships':{'territory':{'data':{'type':'territories','id':'USA'}}}}]}
s,j=call('POST','/v2/appAvailabilities',body);print('avail',s,json.dumps(j)[:800] if s>=300 else j['data']['id'])
