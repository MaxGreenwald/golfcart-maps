// CarPlay bridge. The native CarPlay scene (ios/App/App/CarPlay*.swift) calls these through
// WKWebView.callAsyncJavaScript so CarPlay uses exactly the same rules, data and A* router as
// the phone/web app. Everything returns plain JSON. No effect on the website unless called.
(function(){
const R2D=180/Math.PI;
const brg=(a,b)=>{const r=Math.PI/180,y=Math.sin((b[0]-a[0])*r)*Math.cos(b[1]*r),x=Math.cos(a[1]*r)*Math.sin(b[1]*r)-Math.sin(a[1]*r)*Math.cos(b[1]*r)*Math.cos((b[0]-a[0])*r);return (Math.atan2(y,x)*R2D+360)%360};
const turnOf=d=>{d=((d+540)%360)-180;const a=Math.abs(d);if(a<25)return 'straight';if(a<60)return d>0?'slight_right':'slight_left';if(a<150)return d>0?'right':'left';return 'uturn'};
const inBox=(r,lat,lon)=>lat>=r.bbox[0]&&lat<=r.bbox[2]&&lon>=r.bbox[1]&&lon<=r.bbox[3];
async function ready(){await READY;for(let i=0;i<200&&!window.ready;i++)await new Promise(r=>setTimeout(r,50))}
// Analytics: everything CarPlay triggers is tagged platform 'carplay' (public/track.js; town level only).
const CP={platform:'carplay'};
async function asCarPlay(f){const prev=window._trackOpts;window._trackOpts=CP;try{return await f()}finally{window._trackOpts=prev}}
async function regionFor(lat,lon){if(REG&&inBox(REG,lat,lon))return;const r=REGIONS.find(x=>inBox(x,lat,lon));if(r){window._regHow='carplay';await asCarPlay(async()=>{await loadRegion(r.id,true);await ready()})}}
// Native hooks call these (CarPlaySceneDelegate.swift via GCMBridge): connect -> session, Go -> route_started, arrival -> route_completed.
const CP_EVENTS={session:1,route_started:1,route_completed:1};
function cpTrack(name,props){if(!CP_EVENTS[name])return {ok:false,reason:'not allowed'};const p={};if(props&&props.mi!=null&&isFinite(+props.mi))p.mi=Math.round(+props.mi*2)/2;
 if(!window.GCMTrack)return {ok:false,reason:'no tracker'};window.GCMTrack.track(name,p,name==='session'?{platform:'carplay',force:true}:CP);return {ok:true,event:name,platform:'carplay',props:p}}
function maneuvers(r){
 // group legs by street name + risky flag, keep geometry, then derive turn types at joins
 const g=[];for(const l of r.legs){const n=D.names[l.s[0]]||'unnamed road',last=g[g.length-1];
  if(last&&last.n===n&&last.f===l.f){last.d+=l.s._len;last.p.push(...l.p)}else g.push({n,f:l.f,d:l.s._len,p:l.p.slice(),sp:l.s[2]})}
 const m=g.filter((s,i)=>s.d>15||i===0);const out=[];
 m.forEach((s,i)=>{let type='depart';if(i>0){const pv=m[i-1].p,a=pv[Math.max(0,pv.length-2)],j=pv[pv.length-1],b=s.p[Math.min(1,s.p.length-1)];type=turnOf(brg(j,b)-brg(a,j))}
  out.push({type,road:s.n,meters:Math.round(s.d),risky:!!s.f,mph:s.sp&&s.sp!==99?s.sp:null,lat:s.p[0][1],lon:s.p[0][0],
   text:(type==='depart'?'Head out on ':type==='straight'?'Continue on ':type==='uturn'?'Make a U-turn onto ':'Turn '+type.replace('slight_','slight ')+' onto ')+s.n+(s.f?' (risky stretch)':'')})});
 const e=r.legs.length?r.legs[r.legs.length-1].p:null;if(e){const q=e[e.length-1];out.push({type:'arrive',road:'',meters:0,risky:false,lat:q[1],lon:q[0],text:'Arrive at destination'})}
 return out}
window.GCMCarPlay={
 version:2,
 track:cpTrack,
 async status(){await ready();return {region:REG&&REG.id,regionName:REG&&REG.short,mode:MODE,center:REG&&REG.center,
  regions:REGIONS.map(r=>({id:r.id,name:r.short||r.name,center:r.center,hidden:!!r.hidden})),range:GCMRange.rangeFor(),battery:(GCMRange.load().battery??100)}},
 async setMode(m){await ready();return 'lsv'},  // mode switch removed; always LSV rules
 // from/to: {lat,lon}. Returns null-route with reason when there's no legal way.
 async plan(from,to,mode,allowRisky){await ready();await regionFor(to.lat,to.lon);
  const lr=await asCarPlay(()=>window.testRoute([from.lat,from.lon],[to.lat,to.lon],!!allowRisky));const r=window._lastDetail;
  if(!lr||!r)return {ok:false,reason:RULE.designated_only?'Every way there leaves the cart paths/designated roads.':`Every way there uses a ${RULE.max_posted+5}+ mph road.`};
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
