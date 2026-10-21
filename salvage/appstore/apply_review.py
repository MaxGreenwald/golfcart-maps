import sys,json
sys.path.insert(0,'/workspace/ascapi')
from asc import call
V='5eff07f6-75c3-474d-bef7-d0c12a17e21d'
a={'contactFirstName':'Max','contactLastName':'Greenwald','contactEmail':'max@golfcartmap.com','contactPhone':'+1 303 887 7689','demoAccountRequired':False,'notes':open('review_notes.txt').read().strip()}
s,j=call('POST','/v1/appStoreReviewDetails',{'data':{'type':'appStoreReviewDetails','attributes':a,'relationships':{'appStoreVersion':{'data':{'type':'appStoreVersions','id':V}}}}})
print(s,json.dumps(j)[:600] if s>=300 else j['data']['id'])
