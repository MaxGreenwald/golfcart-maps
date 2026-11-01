// CarPlay bridge. The native CarPlay scene (ios/App/App/CarPlay*.swift) calls these through
// WKWebView.callAsyncJavaScript so CarPlay uses exactly the same rules, data and A* router as
// the phone app. In the native shell, livedata.js fills REGIONS from https://golfcartmap.com
// (bundled files if that fetch fails or the schema does not match), so a town added on the site
// shows up here without a new app build. Everything returns plain JSON. No effect on the website unless called.
(function(){
const R2D=180/Math.PI;
const brg=(a,b)=>{const r=Math.PI/180,y=Math.sin((b[0]-a[0])*r)*Math.cos(b[1]*r),x=Math.cos(a[1]*r)*Math.sin(b[1]*r)-Math.sin(a[1]*r)*Math.cos(b[1]*r)*Math.cos((b[0]-a[0])*r);return (Math.atan2(y,x)*R2D+360)%360};
const turnOf=d=>{d=((d+540)%360)-180;const a=Math.abs(d);if(a<25)return 'straight';if(a<60)return d>0?'slight_right':'slight_left';if(a<150)return d>0?'right':'left';return 'uturn'};
const inBox=(r,lat,lon)=>lat>=r.bbox[0]&&lat<=r.bbox[2]&&lon>=r.bbox[1]&&lon<=r.bbox[3];
async function ready(){await READY;for(let i=0;i<200&&!window.ready;i++)await new Promise(r=>setTimeout(r,50));if(window.vehSync)await window.vehSync()}  // pick up the phone's Golf cart mode setting
// Analytics: everything CarPlay triggers is tagged platform 'carplay' (public/track.js; town level only).
const CP={platform:'carplay'};
async function asCarPlay(f){const prev=window._trackOpts;window._trackOpts=CP;try{return await f()}finally{window._trackOpts=prev}}
async function regionFor(lat,lon){if(REG&&inBox(REG,lat,lon))return;const r=REGIONS.find(x=>inBox(x,lat,lon));if(r){window._regHow='carplay';await asCarPlay(async()=>{await loadRegion(r.id,true);await ready()})}}
// Native hooks call these (CarPlaySceneDelegate.swift via GCMBridge): connect -> session, Go -> route_started, arrival -> route_completed.
const CP_EVENTS={session:1,route_started:1,route_completed:1};
function cpTrack(name,props){if(!CP_EVENTS[name])return {ok:false,reason:'not allowed'};const p={};if(props&&props.mi!=null&&isFinite(+props.mi))p.mi=Math.round(+props.mi*2)/2;
 if(!window.GCMTrack)return {ok:false,reason:'no tracker'};window.GCMTrack.track(name,p,name==='session'?{platform:'carplay',force:true}:CP);return {ok:true,event:name,platform:'carplay',props:p}}
function maneuvers(r){
 // group legs by street name + risky flag, keep geometry, then derive turn types at joins.
 // Each maneuver: meters = length of the road AFTER it; toMeters = distance driven to reach it (CPManeuver.initialTravelEstimates);
 // inBrg/outBrg/turn = approach + exit bearings and signed turn angle (junction diagram, CPManeuver junctionExitAngle).
 const g=[];for(const l of r.legs){const n=D.names[l.s[0]]||'unnamed road',last=g[g.length-1];
  if(last&&last.n===n&&last.f===l.f){last.d+=l.s._len;last.p.push(...l.p)}else g.push({n,f:l.f,d:l.s._len,p:l.p.slice(),sp:l.s[2]})}
 const m=g.filter((s,i)=>s.d>15||i===0);const out=[];
 m.forEach((s,i)=>{let type='depart',turn=0,inB=null,outB=null;const b=s.p[Math.min(1,s.p.length-1)];outB=Math.round(brg(s.p[0],b));
  if(i>0){const pv=m[i-1].p,a=pv[Math.max(0,pv.length-2)],j=pv[pv.length-1];inB=Math.round(brg(a,j));turn=Math.round(((brg(j,b)-brg(a,j)+540)%360)-180);type=turnOf(turn)}
  const verb=type==='depart'?'Head out on ':type==='straight'?'Continue on ':type==='uturn'?'Make a U-turn onto ':'Turn '+type.replace('slight_','slight ')+' onto ';
  out.push({type,road:s.n,meters:Math.round(s.d),toMeters:i>0?Math.round(m[i-1].d):0,turn,inBrg:inB,outBrg:outB,risky:!!s.f,mph:s.sp&&s.sp!==99?s.sp:null,lat:s.p[0][1],lon:s.p[0][0],
   text:verb+s.n+(s.f?' (risky stretch)':''),
   short:(type==='depart'?'Head out on ':type==='straight'?'Continue on ':type==='uturn'?'U-turn onto ':(type.startsWith('slight_')?'Slight '+type.slice(7):type[0].toUpperCase()+type.slice(1))+' onto ')+s.n})});
 // a "Continue on unnamed road" is noise on screen: fold it into the previous step
 for(let i=out.length-1;i>0;i--){const x=out[i];if(x.type==='straight'&&x.road==='unnamed road'){out[i-1].meters+=x.meters;if(out[i+1])out[i+1].toMeters=out[i-1].meters;out.splice(i,1)}}
 const e=r.legs.length?r.legs[r.legs.length-1].p:null;if(e){const q=e[e.length-1];const L=out.length>0?out[out.length-1].meters:0;out.push({type:'arrive',road:'',meters:0,toMeters:Math.round(L),turn:0,inBrg:null,outBrg:null,risky:false,lat:q[1],lon:q[0],text:'Arrive at destination',short:'Arrive'})}
 return out}

// CarPlay Experiences: the renter access the phone saved (p.js / app.js partner overlay, key 'gcm_partner_access').
// Short fields only (CarPlay driver-distraction rules): no descriptions. Access older than 14 days is ignored.
const XP_KEY='gcm_partner_access',XP_DAYS=14;
// The saved unlock answer is used as is: calling unlock again would count another code use.
const xpDist=(a,b,c,d)=>{const r=Math.PI/180,x=(d-b)*r*Math.cos((a+c)/2*r),y=(c-a)*r;return Math.round(Math.sqrt(x*x+y*y)*6371000)};
async function xpLoad(){let a=null;try{a=JSON.parse(localStorage.getItem(XP_KEY)||'null')}catch(_){}
 if(!a||!a.slug||!Array.isArray(a.experiences)||!(Date.now()-(+a.at||0)<XP_DAYS*864e5))return {ok:false,reason:'No rental code yet. Tap the gear to enter one, or enter it in Settings in the phone app.'};
 return {ok:true,slug:a.slug,j:a}}
window.GCMCarPlay={
 // Rental code typed in CarPlay (Max t449u): one code use, saved like the phone's Settings row.
 async enterCode(code){if(!window.GCMRental)return {ok:false,reason:'Enter your code in the phone app.'};const r=await GCMRental.enter(code,{fetch:fetch.bind(window),storage:localStorage,win:window});
  return r.ok?{ok:true,shop:(r.access.shop&&r.access.shop.name)||r.access.slug,experiences:r.access.experiences.length}:r},
 // Active rental shop for the CarPlay settings screen, or {ok:false}.
 rental(){const a=window.GCMRental&&GCMRental.load(localStorage);return a?{ok:true,shop:(a.shop&&a.shop.name)||a.slug,code:a.code}:{ok:false}},
 removeRental(){if(window.GCMRental)GCMRental.remove(localStorage);return {ok:true}},
 version:2,
 track:cpTrack,
 // Experiences for the renter access on this phone, or {ok:false,reason}. vehicle: the shop's rules (golf_cart unless 'lsv').
 async experiences(){const x=await xpLoad();if(!x.ok)return x;const j=x.j,sh=j.shop||{};
  return {ok:true,shop:{slug:x.slug,name:sh.name||'',vehicle:sh.vehicle==='lsv'?'lsv':'golf_cart'},
   experiences:(j.experiences||[]).map(e=>({id:String(e.id),title:e.title||'Experience',stops:(e.stops||[]).filter(s=>isFinite(+s.lat)&&isFinite(+s.lon)&&s.lat!==null&&s.lon!==null).length})).filter(e=>e.stops>0),
   offers:(j.affiliates||[]).map(a=>({name:a.name||'',offer:a.offer||'',coupon:a.coupon||''}))}},
 // Ordered stops of one experience with distance from lat/lon (meters, null without a fix). coupon: the matching partner offer's code, if any.
 async stops(id,lat,lon){const x=await xpLoad();if(!x.ok)return x;const e=(x.j.experiences||[]).find(e=>String(e.id)===String(id));if(!e)return {ok:false,reason:'Experience not found'};
  const af=x.j.affiliates||[];
  return {ok:true,title:e.title||'',stops:(e.stops||[]).filter(s=>s.lat!==null&&s.lon!==null&&isFinite(+s.lat)&&isFinite(+s.lon)).map(s=>{const a=af.find(a=>(s.affiliate_id&&a.id===s.affiliate_id)||(a.name&&a.name===s.name));
   return {name:s.name||'Stop',category:s.category||'',lat:+s.lat,lon:+s.lon,meters:lat==null?null:xpDist(+lat,+lon,+s.lat,+s.lon),coupon:a&&a.coupon||''}})}},
 async status(){await ready();return {region:REG&&REG.id,regionName:REG&&REG.short,mode:MODE,center:REG&&REG.center,
  regions:REGIONS.map(r=>({id:r.id,name:r.short||r.name,center:r.center,hidden:!!r.hidden})),range:GCMRange.rangeFor(),battery:(GCMRange.load().battery??100)}},
 // vehicle = phone Settings > Golf cart mode (localStorage 'gcm-veh', default 'lsv'); setMode changes it for phone + CarPlay
 async setMode(m){await ready();if((m==='golf_cart'||m==='lsv')&&m!==MODE){window.setVeh(m);await READY;for(let i=0;i<200&&!window.ready;i++)await new Promise(r=>setTimeout(r,50))}return MODE},
 // `mode` arg is ignored on purpose (native still passes a fixed 'lsv'); the saved setting decides.
 // from/to: {lat,lon}. Returns null-route with reason when there's no legal way.
 async plan(from,to,mode,allowRisky){await ready();await regionFor(to.lat,to.lon);
  const lr=await asCarPlay(()=>window.testRoute([from.lat,from.lon],[to.lat,to.lon],!!allowRisky&&!window.GCM_IOS));const r=window._lastDetail;
  if(!lr||!r)return {ok:false,reason:GCMRule.noRoute(RULE)};
  const line=[];r.legs.forEach(l=>l.p.forEach(p=>line.push([+p[1].toFixed(6),+p[0].toFixed(6)])));
  return {ok:true,mode:MODE,region:REG.id,meters:Math.round(r.dist),miles:lr.mi,roundTripMiles:lr.rt,minutes:lr.min,range:lr.range,
   risky:lr.risky,line,maneuvers:maneuvers(r)}},
 // legal-road overlay for the visible CarPlay map. Returns up to `max` polylines: ok (green) + avoid (red).
 async overlay(s,w,n,e,max){await ready();await regionFor((s+n)/2,(w+e)/2);await ensure(s,w,n,e);max=max||1500;const ok=[],bad=[];
  for(const x of D.segs){if(ok.length+bad.length>=max)break;const p=x[7];let hit=false;for(const q of p)if(q[1]>=s&&q[1]<=n&&q[0]>=w&&q[0]<=e){hit=true;break}
   if(!hit)continue;(cls(x)===3?bad:ok).push(p.map(q=>[+q[1].toFixed(6),+q[0].toFixed(6)]))}
  return {ok,bad}},
 async search(q,lat,lon){await ready();if(lat!=null)await regionFor(lat,lon);return localMatches(q).map(x=>({name:x.name,sub:x.sub,lat:x.lat,lon:x.lon}))}
};
})();
