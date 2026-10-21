import sys,os,hashlib,requests,json,time
sys.path.insert(0,'/workspace/ascapi')
from asc import call
VL='c964831b-15e3-4d52-b32e-ab3ce7589ad8'
SETS={'APP_IPHONE_67':'screenshots/iphone_6.9','APP_IPAD_PRO_3GEN_129':'screenshots/ipad_13'}
s,j=call('GET',f'/v1/appStoreVersionLocalizations/{VL}/appScreenshotSets');exist={x['attributes']['screenshotDisplayType']:x['id'] for x in j['data']}
for typ,d in SETS.items():
    sid=exist.get(typ)
    if not sid:
        s,j=call('POST','/v1/appScreenshotSets',{'data':{'type':'appScreenshotSets','attributes':{'screenshotDisplayType':typ},'relationships':{'appStoreVersionLocalization':{'data':{'type':'appStoreVersionLocalizations','id':VL}}}}})
        assert s==201,(s,j);sid=j['data']['id']
    s,j=call('GET',f'/v1/appScreenshotSets/{sid}/appScreenshots')
    have={x['attributes']['fileName'] for x in j['data']}
    for f in sorted(os.listdir(d)):
        if f in have: print('skip',typ,f);continue
        b=open(os.path.join(d,f),'rb').read()
        s,j=call('POST','/v1/appScreenshots',{'data':{'type':'appScreenshots','attributes':{'fileName':f,'fileSize':len(b)},'relationships':{'appScreenshotSet':{'data':{'type':'appScreenshotSets','id':sid}}}}})
        assert s==201,(s,j);aid=j['data']['id']
        for op in j['data']['attributes']['uploadOperations']:
            h={x['name']:x['value'] for x in op['requestHeaders']}
            r=requests.request(op['method'],op['url'],headers=h,data=b[op['offset']:op['offset']+op['length']]);assert r.status_code<300,r.text
        s,j=call('PATCH',f'/v1/appScreenshots/{aid}',{'data':{'type':'appScreenshots','id':aid,'attributes':{'uploaded':True,'sourceFileChecksum':hashlib.md5(b).hexdigest()}}})
        print(typ,f,s)
time.sleep(15)
for typ in SETS:
    s,j=call('GET',f'/v1/appStoreVersionLocalizations/{VL}/appScreenshotSets');sid={x['attributes']['screenshotDisplayType']:x['id'] for x in j['data']}[typ]
    s,j=call('GET',f'/v1/appScreenshotSets/{sid}/appScreenshots')
    print(typ,[(x['attributes']['fileName'],x['attributes']['assetDeliveryState']['state']) for x in j['data']])
