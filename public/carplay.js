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
// CarPlay maneuvers are the phone's steps (navStepsFor -> GCMNav.buildSteps), one for one, so the engine's step
// index (navFix idx) is the CarPlay card index (t459u). Only CarPlay display fields are added here.
// meters = length of the road AFTER it; toMeters = distance driven to reach it; turn = signed angle (+ right).
const cpType=s=>s.kind==='arrive'?'arrive':s.kind==='depart'?'depart':s.kind==='continue'?'straight':Math.abs(s.turn||0)>=160?'uturn':s.mod.startsWith('slight')?'slight_'+s.mod.split(' ')[1]:s.mod.split(' ').pop();
function maneuvers(r,route){
 const legAt=ll=>r.legs.find(l=>l.p.length&&Math.abs(l.p[0][1]-ll[0])<1e-6&&Math.abs(l.p[0][0]-ll[1])<1e-6);
 return route.steps.map((s,i)=>{const type=i===0&&r.ahead?'straight':cpType(s),road=s.name||(s.kind==='arrive'?'':'unnamed road'),l=legAt(s.ll);
  const short=type==='arrive'?'Arrive':type==='depart'?'Head out on '+road:type==='straight'?'Continue on '+road:type==='uturn'?'U-turn onto '+road:(type.startsWith('slight_')?'Slight '+type.slice(7):type[0].toUpperCase()+type.slice(1))+' onto '+road;
  return {type,road,meters:Math.round(s.len||0),toMeters:i>0?Math.round(route.steps[i-1].len||0):0,turn:s.turn||0,inBrg:s.inBrg!=null?Math.round(s.inBrg):null,outBrg:s.outBrg!=null?Math.round(s.outBrg):(i===0&&route.pts.length>1?Math.round(GCMNav.bearing(route.pts[0],route.pts[1])):null),
   risky:!!(l&&l.f),mph:l&&l.s[2]&&l.s[2]!==99?l.s[2]:null,lat:s.ll[0],lon:s.ll[1],text:s.text,short}})}
// Live guidance for CarPlay through the SAME engine the phone uses (GCMFollow.engine). Native sends every GPS fix
// and only renders what comes back (card index, distances, map heading, reroute, arrival).
let cpNav=null,cpLast=null,cpPlan=null,cpArrived=false;
const navOut=(st,reroute,say)=>({idx:st.idx,off:Math.round(st.off),along:Math.round(st.along),toNext:Math.round(st.toNext),remaining:Math.round(st.remaining),arrived:!!st.arrived,
 bearing:st.bearing==null?null:Math.round(st.bearing),course:st.course==null?null:Math.round(st.course),reroute:reroute||null,say:say||null});

// CarPlay Experiences: the renter access the phone saved (p.js / app.js partner overlay, key 'gcm_partner_access').
// Short fields only (CarPlay driver-distraction rules): no descriptions. Access older than 14 days is ignored.
const XP_KEY='gcm_partner_access',XP_DAYS=14;
// The saved unlock answer is used as is: calling unlock again would count another code use.
const xpDist=(a,b,c,d)=>{const r=Math.PI/180,x=(d-b)*r*Math.cos((a+c)/2*r),y=(c-a)*r;return Math.round(Math.sqrt(x*x+y*y)*6371000)};
async function xpLoad(){let a=null;try{a=JSON.parse(localStorage.getItem(XP_KEY)||'null')}catch(_){}
 if(!a||!a.slug||!Array.isArray(a.experiences)||!(Date.now()-(+a.at||0)<XP_DAYS*864e5))return {ok:false,reason:'Open your rental shop link on your phone to unlock experiences.'};
 return {ok:true,slug:a.slug,j:a}}
window.GCMCarPlay={
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
 // heading: GPS course while driving (native passes it on reroute, Max t433u). The plan then starts ahead on the
 // current road ("Continue on X") instead of behind you; null/omitted keeps any direction.
 async plan(from,to,mode,allowRisky,heading,dest){await ready();await regionFor(to.lat,to.lon);
  const lr=await asCarPlay(()=>window.testRoute([from.lat,from.lon],[to.lat,to.lon],!!allowRisky&&!window.GCM_IOS,Number.isFinite(heading)?heading:null));const r=window._lastDetail;
  if(!lr||!r)return {ok:false,reason:GCMRule.noRoute(RULE)};
  const route=window.navStepsFor(r,dest||'');cpLast=route;
  const line=route.pts.map(p=>[+p[0].toFixed(6),+p[1].toFixed(6)]);
  return {ok:true,mode:MODE,region:REG.id,meters:Math.round(r.dist),miles:lr.mi,roundTripMiles:lr.rt,minutes:lr.min,range:lr.range,
   risky:lr.risky,line,maneuvers:maneuvers(r,route)}},
 // Start live guidance on the last plan() (Go, or after a reroute plan). Same engine as the phone.
 // Speech comes from the phone's promptPlan too (t459u): native only speaks `say` through GCMVoice, never its own timing.
 navStart(){if(!cpLast)return {ok:false,reason:'no plan'};cpNav=GCMFollow.engine(cpLast);cpPlan=GCMFollow.promptPlan();cpArrived=false;return {ok:true,steps:cpLast.steps.length,say:cpLast.steps[0].text}},
 // One GPS fix {lat,lon,course,speed,accuracy,t (ms)}. reroute: {reason, course} once when the phone rules say so.
 navFix(f){if(!cpNav||!f)return null;const now=Number.isFinite(+f.t)&&f.t!==null?+f.t:Date.now();
  const st=cpNav.fix({latitude:+f.lat,longitude:+f.lon,heading:f.course>=0?+f.course:null,speed:f.speed>=0?+f.speed:null},now);
  const rr=cpNav.offCheck(now)?{reason:'off route '+Math.round(st.off)+' m',course:st.course}:null;if(rr)cpNav.reset();
  let say=null;if(rr)say='Rerouting';else if(st.arrived){if(!cpArrived){cpArrived=true;say=cpLast.steps[cpLast.steps.length-1].text}}else say=cpPlan.update(st,f.speed>=0?+f.speed:null);
  return navOut(st,rr,say)},
 navEnd(){cpNav=null;cpPlan=null;return {ok:true}},
 // legal-road overlay for the visible CarPlay map. Returns up to `max` polylines: ok (green) + avoid (red).
 async overlay(s,w,n,e,max){await ready();await regionFor((s+n)/2,(w+e)/2);await ensure(s,w,n,e);max=max||1500;const ok=[],bad=[];
  for(const x of D.segs){if(ok.length+bad.length>=max)break;const p=x[7];let hit=false;for(const q of p)if(q[1]>=s&&q[1]<=n&&q[0]>=w&&q[0]<=e){hit=true;break}
   if(!hit)continue;(cls(x)===3?bad:ok).push(p.map(q=>[+q[1].toFixed(6),+q[0].toFixed(6)]))}
  return {ok,bad}},
 // Saved places on this phone (Home, Favorite beach, favorites) for CarPlay's Places list and empty search (Max t451u).
 async places(){const G=window.GCMPlaces||globalThis.GCMPlaces;if(!G)return [];const P=G.make(localStorage);
  return P.saved().map(p=>({name:P.label(p),sub:p.id.startsWith('fav')?'Favorite':(p.name&&p.name!==P.label(p)?p.name:''),lat:+p.lat,lon:+p.lon}))},
 async search(q,lat,lon){await ready();if(lat!=null)await regionFor(lat,lon);return localMatches(q).map(x=>({name:x.name,sub:x.sub,lat:x.lat,lon:x.lon}))}
};
})();
