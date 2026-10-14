"""Fetch public Level 1/2 EV chargers per region from US DOE AFDC (NREL/NLR API) -> public/data/<id>/chargers.json"""
import json,urllib.request,os,datetime
KEY=os.environ.get("AFDC_KEY","DEMO_KEY");API="https://developer.nlr.gov/api/alt-fuel-stations/v1.json"
regs=json.load(open("public/data/regions.json"));cache={}
def state(st):
    if st not in cache:
        u=f"{API}?api_key={KEY}&fuel_type=ELEC&status=E&access=public&ev_charging_level=1,2&state={st}&limit=all"
        cache[st]=json.load(urllib.request.urlopen(u,timeout=300))["fuel_stations"]
    return cache[st]
for r in regs:
    s,w,n,e=r["bbox"];out=[]
    for f in state(r["state"]):
        if f.get("access_code")!="public" or not(s<=f["latitude"]<=n and w<=f["longitude"]<=e):continue
        l1,l2=f.get("ev_level1_evse_num") or 0,f.get("ev_level2_evse_num") or 0
        con=f.get("ev_connector_types") or []
        if not(l1 or l2) or not({"J1772","NEMA515","NEMA520","NEMA1450"}&set(con)):continue
        out.append({"id":f["id"],"name":f["station_name"],"lat":round(f["latitude"],6),"lon":round(f["longitude"],6),
          "addr":f"{f.get('street_address') or ''}, {f.get('city') or ''}".strip(", "),"con":con,"l1":l1,"l2":l2,"dc":f.get("ev_dc_fast_num") or 0,
          "hours":f.get("access_days_time"),"network":f.get("ev_network"),"price":f.get("ev_pricing"),"confirmed":f.get("date_last_confirmed")})
    json.dump({"source":"U.S. DOE Alternative Fuels Data Center (afdc.energy.gov)","fetched":datetime.date.today().isoformat(),"stations":out},open(f"public/data/{r['id']}/chargers.json","w"),separators=(",",":"))
    print(r["id"],len(out))
