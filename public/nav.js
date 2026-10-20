// Turn-by-turn navigation core (pure logic, no DOM/Leaflet). Shared by the web app (app.js),
// the Capacitor app (same web bundle) and, later, the CarPlay bridge (carplay.js) so all three
// produce identical maneuvers. Points are [lon,lat] like the road data.
(function(g){
const R2D=180/Math.PI,FT=3.281;
function hav(a,b){const R=6371000,r=Math.PI/180,dl=(b[1]-a[1])*r,dn=(b[0]-a[0])*r,x=Math.sin(dl/2)**2+Math.cos(a[1]*r)*Math.cos(b[1]*r)*Math.sin(dn/2)**2;return 2*R*Math.asin(Math.sqrt(x))}
const brg=(a,b)=>{const r=Math.PI/180,y=Math.sin((b[0]-a[0])*r)*Math.cos(b[1]*r),x=Math.cos(a[1]*r)*Math.sin(b[1]*r)-Math.sin(a[1]*r)*Math.cos(b[1]*r)*Math.cos((b[0]-a[0])*r);return (Math.atan2(y,x)*R2D+360)%360};
const turnOf=d=>{d=((d+540)%360)-180;const a=Math.abs(d);if(a<25)return 'straight';if(a<60)return d>0?'slight_right':'slight_left';if(a<150)return d>0?'right':'left';return 'uturn'};
const COMPASS=['north','northeast','east','southeast','south','southwest','west','northwest'];
const compass=b=>COMPASS[Math.round(b/45)%8];
const UNNAMED='unnamed road';
// Cart speeds (mph) for ETA. Golf carts ~15-19, LSVs ~22-25, slower on residential streets and cart paths.
const SPEED={main:23,res:18,path:12};  // single cart/LSV profile (was LSV)
const RES=new Set(['residential','living_street','service','unclassified','track']);
function mph(mode,leg){const S=SPEED;let v=leg.cart||leg.hw==='path'||leg.hw==='cycleway'||leg.hw==='footway'?S.path:RES.has(leg.hw)?S.res:S.main;if(leg.sp&&leg.sp!==99&&leg.sp<v)v=leg.sp;return v}
// legs: [{p:[[lon,lat]...], name, len(m), f(risky), hw, sp, cart}] in travel order.
function maneuvers(legs,mode){
 const g=[];for(const l of legs){const n=l.name||UNNAMED,last=g[g.length-1],t=l.len/(mph(mode,l)*0.44704);
  if(last&&last.n===n&&last.f===!!l.f){last.d+=l.len;last.t+=t;last.p.push(...l.p.slice(1))}else g.push({n,f:!!l.f,d:l.len,t,p:l.p.slice(),sp:l.sp})}
 // merge tiny (<15 m) groups and unnamed straight "continue" steps into the previous step
 const m=[];for(const s of g){const pv=m[m.length-1];
  if(pv){const a=pv.p[Math.max(0,pv.p.length-2)],j=pv.p[pv.p.length-1],b=s.p[Math.min(1,s.p.length-1)];s.type=turnOf(brg(j,b)-brg(a,j));
   const unnamedCont=(s.n===UNNAMED||s.n===pv.n)&&(s.type==='straight'||s.type.startsWith('slight'))&&s.f===pv.f;
   if(s.d<15||unnamedCont){pv.d+=s.d;pv.t+=s.t;pv.p.push(...s.p.slice(1));continue}}
  else s.type='depart';m.push(s)}
 const out=[];let at=0;
 m.forEach((s,i)=>{const b0=brg(s.p[0],s.p[Math.min(1,s.p.length-1)]);const road=s.n===UNNAMED?'':s.n,onto=road?' onto '+road:'';
  const text=s.type==='depart'?`Head ${compass(b0)}${road?' on '+road:''}`:s.type==='straight'?`Continue${onto||' straight'}`:s.type==='uturn'?'Make a U-turn'+onto:'Turn '+s.type.replace('slight_','slight ')+onto;
  out.push({type:s.type,road,meters:Math.round(s.d),at:Math.round(at),risky:s.f,mph:s.sp&&s.sp!==99?s.sp:null,lat:s.p[0][1],lon:s.p[0][0],text:text+(s.f?' (risky stretch)':''),seconds:s.t});at+=s.d});
 const e=legs.length?legs[legs.length-1].p:null;if(e){const q=e[e.length-1];out.push({type:'arrive',road:'',meters:0,at:Math.round(at),risky:false,lat:q[1],lon:q[0],text:'Arrive at your destination',seconds:0})}
 return out}
// spoken distance: feet under ~0.2 mi (rounded to 50/100 ft), else tenths of a mile
function sayDist(m){const f=m*FT;if(f<1000)return Math.max(50,Math.round(f/50)*50)+' feet';if(m<322)return Math.round(f/100)*100+' feet';const x=m/1609.34;const v=x.toFixed(1).replace(/\.0$/,'');return v+(v==='1'?' mile':' miles')}
function showDist(m){const f=m*FT;return f<1000?Math.max(10,Math.round(f/10)*10)+' ft':(m/1609.34).toFixed(1)+' mi'}
function line(legs,mode){const pts=[],cum=[],tim=[],li=[],legAt=[];let d=0,t=0;
 legs.forEach((l,k)=>{const v=mph(mode,l)*0.44704;legAt.push(d);for(let i=0;i<l.p.length;i++){const q=l.p[i];if(pts.length){const s=hav(pts[pts.length-1],q);if(i===0&&s<0.5)continue;d+=s;t+=s/v}pts.push(q);cum.push(d);tim.push(t);li.push(k)}});
 return {pts,cum,tim,li,legAt,total:d,totalT:t}}
// restricted spots along the route, in route metres: start of each risky stretch (f) and each crossing of a road over the limit (xing)
function hazards(legs,L){const out=[];let prevF=false;legs.forEach((l,k)=>{const at=L.legAt[k];if(l.f&&!prevF)out.push({at,kind:'risky',road:l.name||'',mph:l.sp&&l.sp!==99?l.sp:null});
  if(l.xing)out.push({at:at+l.len,kind:'cross',road:l.xing.name||'',mph:l.xing.sp&&l.xing.sp!==99?l.xing.sp:null});prevF=!!l.f});return out}
function hazardText(h,d,limitTxt){const dist=sayDist(d);const lim=limitTxt||'non-LSV';return h.kind==='risky'?`${lim[0].toUpperCase()+lim.slice(1)} road ahead in ${dist}${h.road?': '+h.road:''}. Risky stretch.`:`Crossing a ${lim} road in ${dist}${h.road?': '+h.road:''}. Cross only at the intersection.`}

// project p onto polyline; search near the last index first (prevents jumping to a parallel loop)
function project(L,p,from){const kx=Math.cos(p[1]*Math.PI/180),M=111320;let best=null;
 const scan=(a,b)=>{for(let i=Math.max(1,a);i<Math.min(L.pts.length,b);i++){const A=L.pts[i-1],B=L.pts[i],ax=(A[0]-p[0])*kx*M,ay=(A[1]-p[1])*M,bx=(B[0]-p[0])*kx*M,by=(B[1]-p[1])*M,dx=bx-ax,dy=by-ay,l2=dx*dx+dy*dy;let t=l2?-(ax*dx+ay*dy)/l2:0;t=Math.max(0,Math.min(1,t));const ex=ax+t*dx,ey=ay+t*dy,dd=Math.sqrt(ex*ex+ey*ey);
  if(!best||dd<best.dist-0.01)best={dist:dd,i,s:L.cum[i-1]+t*(L.cum[i]-L.cum[i-1]),tt:L.tim[i-1]+t*(L.tim[i]-L.tim[i-1])}}};
 scan((from||1)-3,(from||1)+60);if(!best||best.dist>25){const b0=best;best=null;scan(1,L.pts.length);if(b0&&best&&best.dist>b0.dist-5)best=b0}return best}
const DEF={hazardM:180,offRouteM:40,offRouteMs:4000,offRouteFixes:2,arriveM:20,minFarM:120,maxFarM:200,farSec:25,nearSec:4,minNearM:20};
// Navigator: feed it GPS fixes with update({lat,lon,t,acc,speed}); it calls hooks:
// say(text), onUpdate(state), reroute(pos) -> Promise<legs|null>, onArrive().
class Navigator{
 constructor(legs,mode,hooks,opt){this.h=hooks||{};this.o={...DEF,...(opt||{})};this.mode=mode||'lsv';this.state='idle';this.log=[];this.setRoute(legs,true)}
 setRoute(legs,first){this.legs=legs;this.L=line(legs,this.mode);this.man=maneuvers(legs,this.mode);this.ann={};this.hz=hazards(legs,this.L);this.hzSaid={};this.idx=1;this.next=1;this.off=null;this.s=0;this.tt=0;if(!first)this.say('Route updated.')}
 say(t){this.log.push(t);this.h.say&&this.h.say(t)}
 start(){this.state='nav';const m=this.man[0];this.say(m?m.text+(this.man.length>2?`, then in ${sayDist(this.man[1].at)}, ${this.lower(this.man[1].text)}`:'')+'.':'Starting route.');this.ann[0]={far:1,near:1};this.emit()}
 lower(t){return t.charAt(0).toLowerCase()+t.slice(1)}
 stop(){this.state='ended';this.emit()}
 speed(){return Math.max(3,this.v||mph(this.mode,{hw:'residential'})*0.44704)}
 update(f){if(this.state!=='nav'&&this.state!=='off')return this.state;const p=[f.lon,f.lat],t=f.t??Date.now();
  if(this.lastFix){const dt=(t-this.lastFix.t)/1000;if(dt>0.3){const v=f.speed!=null&&f.speed>=0?f.speed:hav(this.lastFix.p,p)/dt;this.v=this.v==null?v:this.v*0.6+v*0.4}}
  this.lastFix={p,t};const pr=project(this.L,p,this.idx);const tol=Math.max(this.o.offRouteM,Math.min(f.acc||0,60));
  if(this.state==='rerouting')return this.state;
  if(!pr||pr.dist>tol){if(!this.off)this.off={t,n:0};this.off.n++;this.state='off';
   if(t-this.off.t>=this.o.offRouteMs&&this.off.n>=this.o.offRouteFixes){this.doReroute(f);return this.state}this.emit();return this.state}
  this.off=null;this.state='nav';this.idx=pr.i;if(pr.s>=this.s-30){this.s=pr.s;this.tt=pr.tt}
  const rem=this.L.total-this.s;
  if(rem<=this.o.arriveM||hav(p,this.L.pts[this.L.pts.length-1])<=this.o.arriveM){this.state='arrived';this.say('You have arrived at your destination.');this.emit();this.h.onArrive&&this.h.onArrive();return this.state}
  for(let k=0;k<this.hz.length;k++){const h=this.hz[k],d=h.at-this.s;if(!this.hzSaid[k]&&d>=0&&d<=this.o.hazardM){this.hzSaid[k]=1;this.say(hazardText(h,Math.max(d,15),this.o.limitTxt))}}
  while(this.next<this.man.length-1&&this.man[this.next].at<=this.s+3)this.next++;
  const m=this.man[this.next],d=m.at-this.s,v=this.speed(),far=Math.min(this.o.maxFarM,Math.max(this.o.minFarM,v*this.o.farSec)),near=Math.max(this.o.minNearM,v*this.o.nearSec),a=this.ann[this.next]||(this.ann[this.next]={});
  const txt=m.type==='arrive'?'your destination is ahead':this.lower(m.text);
  if(!a.near&&d<=near){a.near=a.far=1;this.say(m.type==='arrive'?'Your destination is ahead.':m.text+'.')}
  else if(!a.far&&d<=far&&d>near*1.5){a.far=1;this.say(`In ${sayDist(d)}, ${txt}.`)}
  this.emit();return this.state}
 async doReroute(f){this.state='rerouting';this.say('Off route. Rerouting.');this.emit();let legs=null;try{legs=this.h.reroute?await this.h.reroute(f):null}catch(_){}
  if(this.state!=='rerouting')return;if(legs&&legs.length){this.setRoute(legs);this.state='nav';this.lastReroute=Date.now();this.start2()}else{this.state='off';this.off={t:(f.t??Date.now()),n:0};this.say('No legal route from here yet. Head back toward the blue line.')}this.emit()}
 start2(){this.ann[0]={far:1,near:1};this.emit()}
 info(){const m=this.man[this.next]||null,rem=Math.max(0,this.L.total-this.s),secs=Math.max(0,this.L.totalT-this.tt);
  const li=this.L.li[Math.max(0,this.idx-1)],leg=this.legs[li]||{};const hz=this.hz.find((h,k)=>h.at-this.s>=0&&h.at-this.s<=this.o.hazardM);
  return {limit:leg.cart?null:leg.sp&&leg.sp!==99?leg.sp:null,cartPath:!!leg.cart,assumed:!leg.cart&&(leg.sp==null||leg.sp===99),hazard:hz?{...hz,dist:Math.round(hz.at-this.s)}:null,heading:this.heading(),state:this.state,next:m,nextIndex:this.next,toNext:m?Math.max(0,m.at-this.s):0,then:this.man[this.next+1]||null,remaining:rem,remainingSec:secs,offBy:this.off?1:0}}
 heading(){const i=Math.max(1,this.idx),A=this.L.pts[i-1],B=this.L.pts[Math.min(this.L.pts.length-1,i)];return A&&B&&(A[0]!==B[0]||A[1]!==B[1])?Math.round(brg(A,B)):null}
 emit(){this.h.onUpdate&&this.h.onUpdate(this.info())}
}
g.GCMNav={hazards,hazardText,maneuvers,Navigator,sayDist,showDist,mph,SPEED,line,project,hav,brg,turnOf};
if(typeof module!=='undefined')module.exports=g.GCMNav;
})(typeof window!=='undefined'?window:globalThis);
