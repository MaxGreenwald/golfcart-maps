// Anonymous event sink. Stores no IP, UA string or other personal data. Always 204 so the app never sees errors.
const OK=()=>new Response(null,{status:204,headers:{'Cache-Control':'no-store'}});
const EV=new Set(['app_open','region_change','road_tap','route_planned','route_failed','risky_on','risky_warning_accepted','chargers_tap_locked','checkout_started','unlock_success','restore','locate','start_from_me','voice_nav_start','report_problem','settings_open']);
const SCHEMA="CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,event TEXT NOT NULL,region TEXT,props TEXT,uid TEXT,sid TEXT,device TEXT,pwa INTEGER,country TEXT);\nCREATE INDEX IF NOT EXISTS ev_ts ON events(ts);\nCREATE INDEX IF NOT EXISTS ev_event_ts ON events(event,ts);";
const str=(v,n)=>typeof v==='string'?v.slice(0,n):null;
export async function onRequestPost({request,env}){
  try{
    if(!env.DB)return OK();
    const t=await request.text();if(t.length>4000)return OK();
    const b=JSON.parse(t);if(!b||!EV.has(b.e))return OK();
    let p=b.p&&typeof b.p==='object'?b.p:{};delete p.email;let ps=JSON.stringify(p);if(ps.length>1000)ps='{}';
    const dev=['mobile','tablet','desktop'].includes(b.d)?b.d:null;
    const ins=()=>env.DB.prepare('INSERT INTO events(ts,event,region,props,uid,sid,device,pwa,country) VALUES(?,?,?,?,?,?,?,?,?)')
      .bind(Date.now(),b.e,str(b.r,40),ps,str(b.u,64),str(b.s,64),dev,b.pwa?1:0,(request.cf&&request.cf.country)||null).run();
    try{await ins()}catch(e){if(!/no such table/i.test(String(e&&e.message)))throw e;await env.DB.exec(SCHEMA);await ins()}
  }catch(_){}
  return OK();
}
export const onRequestGet=()=>new Response('POST only',{status:405});
