// Private summary. GET /api/stats?k=<STATS_KEY>&days=30
const J=(o,s=200)=>new Response(JSON.stringify(o,null,1),{status:s,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Robots-Tag':'noindex'}});
function eq(a,b){if(typeof a!=='string'||typeof b!=='string'||a.length!==b.length)return false;let d=0;for(let i=0;i<a.length;i++)d|=a.charCodeAt(i)^b.charCodeAt(i);return d===0}
export async function onRequestGet({request,env}){
  const u=new URL(request.url),k=u.searchParams.get('k')||request.headers.get('x-stats-key')||'';
  if(!env.STATS_KEY||!eq(k,env.STATS_KEY))return J({error:'unauthorized'},401);
  if(!env.DB)return J({error:'D1 binding DB missing'},503);
  const days=Math.min(365,Math.max(1,+u.searchParams.get('days')||30)),since=Date.now()-days*864e5;
  const q=(s,...a)=>env.DB.prepare(s).bind(since,...a).all().then(r=>r.results);
  try{
  const [daily,byType,regions,pwa,dev,countries,funnel,totals]=await Promise.all([
    q("SELECT date(ts/1000,'unixepoch') day,COUNT(DISTINCT uid) users,COUNT(DISTINCT sid) sessions,COUNT(*) events FROM events WHERE ts>=? GROUP BY day ORDER BY day DESC"),
    q("SELECT event,COUNT(*) n,COUNT(DISTINCT uid) users FROM events WHERE ts>=? GROUP BY event ORDER BY n DESC"),
    q("SELECT region,COUNT(DISTINCT uid) users,COUNT(*) events,SUM(event='route_planned') routes FROM events WHERE ts>=? AND region IS NOT NULL GROUP BY region ORDER BY users DESC LIMIT 20"),
    q("SELECT pwa,COUNT(DISTINCT uid) users,COUNT(DISTINCT sid) sessions FROM events WHERE ts>=? AND event='app_open' GROUP BY pwa"),
    q("SELECT device,COUNT(DISTINCT uid) users FROM events WHERE ts>=? GROUP BY device ORDER BY users DESC"),
    q("SELECT country,COUNT(DISTINCT uid) users FROM events WHERE ts>=? GROUP BY country ORDER BY users DESC LIMIT 15"),
    q("SELECT event,COUNT(DISTINCT uid) users FROM events WHERE ts>=? AND event IN ('app_open','chargers_tap_locked','checkout_started','unlock_success','restore') GROUP BY event"),
    q("SELECT COUNT(DISTINCT uid) users,COUNT(DISTINCT sid) sessions,COUNT(*) events FROM events WHERE ts>=?")]);
  const n=e=>(byType.find(x=>x.event===e)||{}).n||0;
  const ok=n('route_planned'),fail=n('route_failed');
  const pu=pwa.reduce((a,x)=>a+x.users,0),pp=(pwa.find(x=>x.pwa===1)||{}).users||0;
  const f=e=>(funnel.find(x=>x.event===e)||{}).users||0;
  const srcs=await q("SELECT json_extract(props,'$.source') source,COUNT(*) n FROM events WHERE ts>=? AND event='app_open' GROUP BY source ORDER BY n DESC");
  return J({days,generated:new Date().toISOString(),totals:totals[0],daily,events:byType,top_regions:regions,
    routes:{planned:ok,failed:fail,success_rate:ok+fail?+(ok/(ok+fail)).toFixed(3):null},
    pwa:{pwa_users:pp,browser_users:pu-pp,pwa_share:pu?+(pp/pu).toFixed(3):null},
    devices:dev,countries,open_sources:srcs,
    paywall_funnel:[['opened app',f('app_open')],['tapped locked chargers',f('chargers_tap_locked')],['started checkout',f('checkout_started')],['unlocked',f('unlock_success')]].map(([step,users])=>({step,users})),
    restores:n('restore')});
  }catch(e){return J({error:/no such table/i.test(e.message)?'no events yet':'query failed'},/no such table/i.test(e.message)?200:500)}
}
