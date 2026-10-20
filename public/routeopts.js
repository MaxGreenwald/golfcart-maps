// routeopts.js: route choices (fastest, most legal, shortest, scenic) as A* edge-cost profiles, plus the
// "% verified" score and duplicate detection. Pure, shared by app.js and scripts/test_routeopts.js.
// Costs are always >= segment length (metres), so app.js's straight-line A* heuristic stays admissible and
// every profile runs on the same legal graph: profiles only re-weight allowed edges, never unlock forbidden ones.
(function(root){
const SPEED={main:23,res:18,path:12},RES=/^(residential|living_street|service|unclassified|track)$/,PATH=/^(path|cycleway|footway|pedestrian)$/;
function mph(s){let v=s[3]==='c'||PATH.test(s[1])?SPEED.path:RES.test(s[1])?SPEED.res:SPEED.main;if(s[2]!=null&&s[2]!==99&&s[2]<v)v=s[2];return Math.max(5,v)}
// verified = the limit comes from a posted/listed source (OSM tag, city list, sign photo) or it's a cart path / designated road
const VER=new Set(['t','v','m','c','d','r','k','n']);
const verified=(s,c)=>c!==3&&VER.has(s[3]);
const SCENIC_HW=/^(residential|living_street|path|cycleway|footway|pedestrian|service)$/;
const PROFILES={
 fastest:{label:'Fastest',icon:'⚡',cost:(s,w)=>w*SPEED.main/mph(s)},
 legal:{label:'Most verified',icon:'✅',cost:(s,w,c,x)=>w*(verified(s,c)?1:1.8)*(x&&x.caution?2.5:1)},
 shortest:{label:'Shortest',icon:'📏',cost:(s,w)=>w},
 scenic:{label:'Scenic',icon:'🌴',cost:(s,w,c,x)=>w*((x&&x.scenic)?1:SCENIC_HW.test(s[1])?1.35:1.9)}};
const ORDER=['fastest','legal','shortest','scenic'];
// % of the route's length on roads with a verified limit (0-100)
function score(legs,clsOf){let tot=0,ok=0;for(const l of legs){const s=l.s,len=s._len||0;tot+=len;if(verified(s,clsOf(s)))ok+=len}return tot?Math.round(ok/tot*100):0}
// two routes are "the same" when they share >= 92% of their length
function same(a,b){const A=new Set(a.map(p=>p[0]));let sh=0,tb=0;for(const [si,,len] of b){tb+=len||1;if(A.has(si))sh+=len||1}let ta=0;for(const p of a)ta+=p[2]||1;return sh/Math.max(ta,tb)>=0.92}
// scenic flag per segment: a scenic road class near a park, beach, viewpoint, golf course or attraction POI (within ~150 m)
const SCENIC_POI=/^(park|beach|viewpoint|golf_course|attraction|nature_reserve|garden|marina|pier)$/;
function scenicIndex(pois,G){G=G||0.004;const idx=new Map();for(const p of pois||[]){if(!SCENIC_POI.test(p[1]))continue;const k=Math.floor(p[2]/G)+','+Math.floor(p[3]/G);(idx.get(k)||idx.set(k,[]).get(k)).push([p[2],p[3]])}
 return s=>{if(s._sc!==undefined)return s._sc;let r=false;if(s[3]==='c'||SCENIC_HW.test(s[1])){const q=s[7][Math.floor(s[7].length/2)],bx=Math.floor(q[0]/G),by=Math.floor(q[1]/G),kx=Math.cos(q[1]*Math.PI/180);
  out:for(let x=bx-1;x<=bx+1;x++)for(let y=by-1;y<=by+1;y++)for(const p of idx.get(x+','+y)||[]){const dx=(p[0]-q[0])*kx*111320,dy=(p[1]-q[1])*111320;if(dx*dx+dy*dy<150*150){r=true;break out}}}
  return s._sc=r}}
const api={PROFILES,ORDER,mph,verified,score,same,scenicIndex,SPEED};
if(typeof module==='object'&&module.exports)module.exports=api;else root.GCMRouteOpts=api;
})(typeof window!=='undefined'?window:globalThis);
