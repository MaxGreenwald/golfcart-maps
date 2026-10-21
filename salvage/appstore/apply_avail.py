import sys,json
sys.path.insert(0,'/workspace/ascapi')
from asc import call
APP='6823958385'
s,j=call('GET','/v1/territories?limit=200');T=[x['id'] for x in j['data']];print(len(T))
inc=[{'type':'territoryAvailabilities','id':f'${{t{i}}}','attributes':{'available':t=='USA'},'relationships':{'territory':{'data':{'type':'territories','id':t}}}} for i,t in enumerate(T)]
body={'data':{'type':'appAvailabilities','attributes':{'availableInNewTerritories':False},'relationships':{'app':{'data':{'type':'apps','id':APP}},'territoryAvailabilities':{'data':[{'type':'territoryAvailabilities','id':x['id']} for x in inc]}}},'included':inc}
s,j=call('POST','/v2/appAvailabilities',body);print('avail',s,json.dumps(j)[:800] if s>=300 else j['data']['id'])
s,j=call('GET',f'/v1/apps/{APP}/appPriceSchedule/manualPrices?include=appPricePoint,territory');print('manual prices',s,json.dumps(j)[:400])
