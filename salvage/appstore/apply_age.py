import sys,json
sys.path.insert(0,'/workspace/ascapi')
from asc import call
AI='b9b5e83c-e32d-4312-970f-c3d5d2629cfe'
NONE=['alcoholTobaccoOrDrugUseOrReferences','contests','gamblingSimulated','gunsOrOtherWeapons','horrorOrFearThemes','matureOrSuggestiveThemes','medicalOrTreatmentInformation','profanityOrCrudeHumor','sexualContentGraphicAndNudity','sexualContentOrNudity','violenceCartoonOrFantasy','violenceRealistic','violenceRealisticProlongedGraphicOrSadistic']
FALSE=['advertising','gambling','healthOrWellnessTopics','lootBox','messagingAndChat','parentalControls','ageAssurance','unrestrictedWebAccess','userGeneratedContent']
a={k:'NONE' for k in NONE}; a.update({k:False for k in FALSE})
s,j=call('PATCH',f'/v1/ageRatingDeclarations/{AI}',{'data':{'type':'ageRatingDeclarations','id':AI,'attributes':a}})
print(s,json.dumps(j)[:1500] if s>=300 else 'ok')
s,j=call('GET',f'/v1/appInfos/{AI}');print(j['data']['attributes'])
