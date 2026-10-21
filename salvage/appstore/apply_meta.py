import sys,json
sys.path.insert(0,'/workspace/ascapi')
from asc import call
d=json.load(open('listing.json'))
d['description']=d['description'].replace("• Get cart-friendly routes that stay off fast roads, crossing them only at intersections.","• Get cart-friendly routes that stay off fast and banned roads.")
json.dump(d,open('listing.json','w'),indent=1)
V='5eff07f6-75c3-474d-bef7-d0c12a17e21d';VL='c964831b-15e3-4d52-b32e-ab3ce7589ad8';AI='b9b5e83c-e32d-4312-970f-c3d5d2629cfe';AIL='78afe696-3dc5-4848-8cec-40829b6f673b'
def p(s,j): print(s, json.dumps(j)[:400] if s>=300 else 'ok')
p(*call('PATCH',f'/v1/appStoreVersionLocalizations/{VL}',{'data':{'type':'appStoreVersionLocalizations','id':VL,'attributes':{k:d[k] for k in ['description','keywords','promotionalText','supportUrl','marketingUrl']}}}))
p(*call('PATCH',f'/v1/appInfoLocalizations/{AIL}',{'data':{'type':'appInfoLocalizations','id':AIL,'attributes':{'subtitle':d['subtitle'],'privacyPolicyUrl':d['privacyPolicyUrl']}}}))
p(*call('PATCH',f'/v1/appStoreVersions/{V}',{'data':{'type':'appStoreVersions','id':V,'attributes':{'copyright':d['copyright']}}}))
p(*call('PATCH',f'/v1/appInfos/{AI}',{'data':{'type':'appInfos','id':AI,'relationships':{'primaryCategory':{'data':{'type':'appCategories','id':'NAVIGATION'}},'secondaryCategory':{'data':{'type':'appCategories','id':'TRAVEL'}}}}}))
p(*call('PATCH','/v1/apps/6823958385',{'data':{'type':'apps','id':'6823958385','attributes':{'contentRightsDeclaration':'USES_THIRD_PARTY_CONTENT'}}}))
