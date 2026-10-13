ENC_URL="https://ecode360.com/EN5042/laws/LF2740111.pdf"
ENC="""Balour Dr|Encinitas Blvd|Melba Rd|25
Balour Dr|Melba Rd|Santa Fe Dr|25
Birmingham Dr|San Elijo Ave|I-5|25
Birmingham Dr|I-5|Lake Dr|30
El Camino Del Norte|Rancho Santa Fe Rd|East City Limits|35
El Camino Real|North City Limits|Garden View Rd|40
El Camino Real|Garden View Rd|Encinitas Blvd|30
El Camino Real|Encinitas Blvd|Santa Fe Dr|35
El Camino Real|Santa Fe Dr|Manchester Ave|45
Encinitas Blvd|Coast Hwy 101|Quail Gardens Rd|35
Encinitas Blvd|Quail Gardens Rd|El Camino Real|40
Encinitas Blvd|El Camino Real|Village Park Way|40
Encinitas Blvd|Village Park Way|Rancho Santa Fe Rd|45
Garden View Rd|Leucadia Blvd|El Camino Real|35
Garden View Rd|El Camino Real|Glen Arbor Dr|35
La Costa Ave|N Coast Hwy 101|East City Limits|30
Lake Dr|Santa Fe Dr|Birmingham Dr|30
Lake Dr|Birmingham Dr|Wales Dr|30
Leucadia Blvd|Coast Hwy 101|I-5|25
Leucadia Blvd|I-5|Quail Gardens Dr|35
Leucadia Blvd|Quail Gardens Dr|El Camino Real|40
Lone Jack Rd|Rancho Santa Fe Rd|North End|35
Mackinnon Ave|Santa Fe Dr|Villa Cardiff|30
Manchester Ave|San Elijo Ave|I-5|35
Manchester Ave|I-5|El Camino Real|40
Manchester Ave|El Camino Real|Encinitas Blvd|35
Mountain Vista Dr|El Camino Real|Glen Arbor Dr|40
N Coast Hwy 101|La Costa Ave|Leucadia Blvd|25
N Coast Hwy 101|Leucadia Blvd|Encinitas Blvd|25
Nardo Rd|Requeza St|Santa Fe Dr|20
Olivenhain Rd|El Camino Real|East City Limits|45
Piraeus St|La Costa Ave|Leucadia Blvd|40
Quail Gardens Dr|Swallowtail Rd|Leucadia Blvd|30
Quail Gardens Dr|Leucadia Blvd|Encinitas Blvd|30
Quail Hollow Dr|Saxony Rd|Swallowtail Rd|30
Rancho Santa Fe Rd|North City Limits|Encinitas Blvd|35
S Rancho Santa Fe Rd|Manchester Ave|East City Limits|35
Requeza St|Vulcan Ave|Nardo Rd|20
S Coast Hwy 101|Encinitas Blvd|D St|25
S Coast Hwy 101|D St|J St|25
S Coast Hwy 101|J St|Swami's|25
S Coast Hwy 101|Swami's|Chesterfield Dr|30
S Coast Hwy 101|Chesterfield Dr|South City Limits|30
San Elijo Ave|Santa Fe Dr|Chesterfield Dr|25
Santa Fe Dr|Vulcan Ave|I-5|25
Santa Fe Dr|I-5|Lake Dr|30
Santa Fe Dr|Lake Dr|El Camino Real|30
Saxony Rd|La Costa Ave|Quail Hollow Rd|40
Saxony Rd|Quail Hollow Rd|Leucadia Blvd|25
Saxony Rd|Leucadia Blvd|Encinitas Blvd|30
Third St|B St|K St|20
Via Cantebria|Garden View Rd|Encinitas Blvd|35
Via Cantebria|Garden View Rd|Town Center Dr|25
Via Molena|Via Cantebria|El Camino Real|25
Via Montoro|Via Cantebria|El Camino Real|30
Villa Cardiff Dr|Mackinnon Ave|Birmingham Dr|30
Village Park Way|Willowspring Dr|Encinitas Blvd|30
Vulcan Ave|La Costa Ave|Leucadia Blvd|25
Vulcan Ave|Leucadia Blvd|Encinitas Blvd|25
Vulcan Ave|Encinitas Blvd|Santa Fe Dr|30
Westlake Dr|Encinitas Blvd|Requeza St|20"""
OC_URL="https://gocodebook.com/library/us/ca/oceanside/oceanside-traffic-code-1/article-xiv-special-speed-zones"
IB_URL="https://gocodebook.com/library/us/ca/imperial-beach/title-10-vehicles-and-traffic/chapter-10.28-special-speed-zones"
import re
def oc():
    out=[]
    for l in open('/workspace/sweep/oc_rows.txt'):
        m=re.match(r'\((\w+)\) \| (.+?) (?:between|from) (.+?) (?:and|to) (.+?) \| (\d+)',l.strip())
        if m: out.append((m.group(2),m.group(3),m.group(4),int(m.group(5)),'Oceanside Traffic Code Art. XIV '+m.group(1)))
    return out
def ib():
    out=[]
    for l in open('/workspace/sweep/ib_rows.txt'):
        m=re.match(r'(.+?) from (.+?) to (.+?) \| (\d+)',l.strip())
        if m: out.append((m.group(1),m.group(2),re.sub(r' \(.*\)','',m.group(3)),int(m.group(4)),'IBMC 10.28.020 (2022 E&TS)'))
    return out
def enc(): return [tuple(x.split('|')[:3])+(int(x.split('|')[3]),'Encinitas Ord. 2026-05 Exhibit A (2026 E&TS)') for x in ENC.splitlines()]
