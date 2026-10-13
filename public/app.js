const map=L.map('map',{preferCanvas:true,zoomControl:false,attributionControl:true}).setView([32.8565,-117.2555],15);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);
const renderer=L.canvas({tolerance:8});
const $=id=>document.getElementById(id);
const RISKY_MAX=91.44; // 300 ft
let REGIONS=[],RULES={},REG=null,MODE=localStorage.getItem('gcm-mode')||'lsv',RULE={max_posted:35,cross:true},BASE='data/sd/';
let D,risky=false,layer,nodes={},adj={},start=null,end=null,routeG=null,mk=[];
// cls: 0 posted ok, 1 assumed ok, 3 forbidden (posted >=40 or untagged major)
// cls: 0 posted ok, 1 assumed ok, 3 forbidden. Cart paths ('c') always ok; designated ('d') ok in designated-only cart mode.
const desig=s=>s[3]==='c'||s[3]==='d'||(RULE.assume&&RULE.assume.includes(s[1])&&s[2]!=null&&s[2]<=RULE.max_posted);
const cls=s=>{if(s[3]==='c')return 0;if(MODE==='golf_cart'&&s[9]===1)return 3;if(s[2]==null||(s[2]>RULE.max_posted&&!(window.LENIENT&&s[2]===99)))return 3;if(RULE.designated_only&&!desig(s))return 3;return s[3]==='t'||s[3]==='v'||s[3]==='m'||s[3]==='d'?0:1};
const STY=[{color:'#12a150',weight:3.2},{color:'#4cc38a',weight:2.6,dashArray:'5 4'},{color:'#0b9fb3',weight:3.4},{color:'#e5484d',weight:3,opacity:.75}];
const MAJOR=new Set(['path','cycleway','track','footway','motorway','motorway_link','trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link']);
let buckets={},shown={};const G=0.02;
function bucketize(from){D.segs.slice(from).forEach((s,j)=>{const i=from+j;const p=s[7][0],k=Math.floor(p[0]/G)+','+Math.floor(p[1]/G);(buckets[k]||(buckets[k]=[])).push(i)})}
function draw(){layer=L.layerGroup().addTo(map);refresh()}
function refresh(){const b=map.getBounds().pad(0.2),z=map.getZoom(),minor=z>=14;
 const x0=Math.floor(b.getWest()/G),x1=Math.floor(b.getEast()/G),y0=Math.floor(b.getSouth()/G),y1=Math.floor(b.getNorth()/G),want={};
 for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){const k=x+','+y;if(buckets[k])want[k+(minor?'m':'')]=k}
 for(const k in shown)if(!(k in want)){layer.removeLayer(shown[k]);delete shown[k]}
 for(const k in want)if(!shown[k]){const g=L.layerGroup();for(const i of buckets[want[k]]){const s=D.segs[i];if(!minor&&!MAJOR.has(s[1]))continue;g.addLayer(mkLine(s))}shown[k]=g;layer.addLayer(g)}}
const loaded=new Set(),loading={};
async function loadTile(k){if(loaded.has(k))return;if(!loading[k])loading[k]=(async()=>{for(let a=0;a<4;a++){try{const r=await fetch(BASE+'tiles/'+k+'.json',{cache:a?'reload':'default'});if(!r.ok)throw new Error('HTTP '+r.status);const segs=await r.json();if(loaded.has(k))return;loaded.add(k);const from=D.segs.length;D.segs.push(...segs);bucketize(from);buildGraph(from);return}catch(e){console.warn('tile',k,e);await new Promise(r=>setTimeout(r,600*(a+1)))}}delete loading[k];$('sub').textContent='⚠️ Couldn’t load road data for this area. Check your connection and try again.';throw new Error('tile '+k)})();return loading[k]}
function tilesIn(s,w,n,e){const T=D.meta.tileSize,out=[];for(let x=Math.floor(w/T);x<=Math.floor(e/T);x++)for(let y=Math.floor(s/T);y<=Math.floor(n/T);y++){const k=x+'_'+y;if(D.tileSet.has(k))out.push(k)}return out}
async function ensure(s,w,n,e){await READY;const ks=tilesIn(s,w,n,e).filter(k=>!loaded.has(k));if(!ks.length)return;let done=0;const msg=()=>{$('sub').textContent=`Loading roads… ${done}/${ks.length} areas`};const prev=$('sub').innerHTML;msg();await Promise.allSettled(ks.map(k=>loadTile(k).then(()=>{done++;msg()})));$('sub').innerHTML=window.ready?prev:'See where you can legally drive. Tap the map to set a start, or hit 📍.'}
async function onMove(){if(!D)return;const b=map.getBounds().pad(0.1);const n0=loaded.size;if(map.getZoom()>=11)await ensure(b.getSouth(),b.getWest(),b.getNorth(),b.getEast());if(loaded.size!==n0){shown={};layer.clearLayers()}refresh()}
map.on('moveend',onMove);
function mkLine(s){const c0=cls(s),c=s[3]==='c'?2:c0;const pl=L.polyline(s[7].map(p=>[p[1],p[0]]),{...STY[c],renderer});
 pl.on('click',e=>{L.DomEvent.stopPropagation(e);if(active){setPt(e.latlng);return}const sp=s[2];window._pll=e.latlng;
  L.popup().setLatLng(e.latlng).setContent(`<b>${D.names[s[0]]||'(unnamed road)'}</b><br>${s[1].replace('_',' ')} · ${sp==null||sp==99?'no limit recorded':sp+' mph'}${s[3]==='c'?' 🛺 cart path':s[3]==='d'?' ✅ designated cart road':s[3]==='t'?' (OSM)':s[3]==='v'?' ✅ verified (local source)':s[3]==='m'?' 📷 posted sign (Mapillary)':' (assumed)'}${(s[3]==='v'||s[3]==='m')&&D.sources&&D.sources[s[8]]?`<br><a href="${D.sources[s[8]][0]}" target="_blank" rel="noopener">Source: ${D.sources[s[8]][1]}</a>`:''}<br><b style="color:${c===3?'#e5484d':'#12a150'}">${c===3?(s[9]===1&&MODE==='golf_cart'?'Avoid: golf carts not allowed (posted)':RULE.designated_only&&!(s[2]==null||s[2]>RULE.max_posted)?'Avoid: not a designated golf cart road':`Avoid: ${RULE.max_posted+5}+ mph or major road`):'OK for '+modeName()}</b><br>Segment length: ${(s._len??len(s[7]))<160?ft(s._len??len(s[7])):mi(s._len??len(s[7]))}<div style="display:flex;gap:6px;margin-top:6px"><button class="pbtn" onclick="popSet('from')">Start here</button><button class="pbtn" onclick="popSet('to')">Go here</button></div>`).openOn(map)});return pl}
function hav(a,b){const R=6371000,r=Math.PI/180,dl=(b[1]-a[1])*r,dn=(b[0]-a[0])*r,x=Math.sin(dl/2)**2+Math.cos(a[1]*r)*Math.cos(b[1]*r)*Math.sin(dn/2)**2;return 2*R*Math.asin(Math.sqrt(x))}
function len(p){let l=0;for(let i=1;i<p.length;i++)l+=hav(p[i-1],p[i]);return l}
let fast=new Set(),fnode=new Set(),cnode=new Set();
function buildGraph(from){D.segs.slice(from).forEach((s,j)=>{const i=from+j;const c=cls(s),a=s[5],b=s[6],p=s[7];s._len??=len(p);nodes[a]=p[0];nodes[b]=p[p.length-1];
  if((s[3]==='t'||s[3]==='m')&&s[2]>RULE.max_posted){fast.add(a);fast.add(b)}if(c===3)fnode.add(a),fnode.add(b);if(s[3]==='c')cnode.add(a),cnode.add(b);
  const f=c===3;
  if(s[4]>=0)(adj[a]||(adj[a]=[])).push([b,s._len,i,false,f]);if(s[4]<=0)(adj[b]||(adj[b]=[])).push([a,s._len,i,true,f])})}
// snap to nearest point on an allowed (non-forbidden) edge; returns the closer endpoint node of that edge
function nearest(ll){const q=[ll.lng,ll.lat],kx=Math.cos(ll.lat*Math.PI/180);let best=null,bd=1e18;
 const T=0.004,bx=Math.floor(q[0]/G),by=Math.floor(q[1]/G);
 const cand=[];for(let x=bx-1;x<=bx+1;x++)for(let y=by-1;y<=by+1;y++)(buckets[x+','+y]||[]).forEach(i=>cand.push(i));
 for(const i of cand){const s=D.segs[i];if(cls(s)===3)continue;const p=s[7];
  for(let j=1;j<p.length;j++){const ax=(p[j-1][0]-q[0])*kx,ay=p[j-1][1]-q[1],bx_=(p[j][0]-q[0])*kx,by_=p[j][1]-q[1];const dx=bx_-ax,dy=by_-ay,L2=dx*dx+dy*dy;let t=L2?-(ax*dx+ay*dy)/L2:0;t=Math.max(0,Math.min(1,t));const ex=ax+t*dx,ey=ay+t*dy,d=ex*ex+ey*ey;
   if(d<bd){bd=d;const da=hav(q,p[0]),db=hav(q,p[p.length-1]);best=[da<=db?s[5]:s[6],da<=db?s[6]:s[5]]}}}
 if(!best)return [null,1e9];return [best[0],Math.sqrt(bd)*111320,best[1]]}
// A* over (node, metres-of-current-forbidden-run). Legal mode: forbidden edges never used.
// Crossing a forbidden road = passing through a shared node between two allowed edges (CVC 21260(b)(1)).
function astar(s,t){const key=(n,r)=>n+'|'+Math.round(r);const T=nodes[t];const g=new Map(),prev=new Map();const k0=key(s,0);g.set(k0,0);
 const h=[[hav(nodes[s],T),s,0,k0]],done=new Set();
 const push=x=>{h.push(x);let i=h.length-1;while(i>0){const p=(i-1)>>1;if(h[p][0]<=h[i][0])break;[h[p],h[i]]=[h[i],h[p]];i=p}};
 const pop=()=>{const top=h[0],l=h.pop();if(h.length){h[0]=l;let i=0;for(;;){let a=2*i+1,b=a+1,m=i;if(a<h.length&&h[a][0]<h[m][0])m=a;if(b<h.length&&h[b][0]<h[m][0])m=b;if(m===i)break;[h[m],h[i]]=[h[i],h[m]];i=m}}return top};
 let goal=null;
 while(h.length){const [,u,run,ku]=pop();if(done.has(ku))continue;done.add(ku);if(u===t&&run===0){goal=ku;break}
  for(const [v,w,si,rev,f] of adj[u]||[]){let nr,cost=w;
   if(!f&&RULE.cross===false&&fnode.has(v)&&!cnode.has(v)&&v!==t)continue;if(f){if(!risky)continue;nr=run+w;if(nr>RISKY_MAX)continue;cost=w*6+60}else{nr=0;if(fast.has(v))cost+=150}
   const kv=key(v,nr),ng=g.get(ku)+cost;if(!g.has(kv)||ng<g.get(kv)){g.set(kv,ng);prev.set(kv,[ku,si,rev]);push([ng+hav(nodes[v],T),v,nr,kv])}}}
 if(!goal)return null;const parts=[];let x=goal;while(x!==k0){const [pk,si,rev]=prev.get(x);parts.push([si,rev]);x=pk}parts.reverse();return parts}
function summarize(parts){let dist=0,stretches=[],cur=null,line=[];const legs=[];
 for(const [si,rev] of parts){const s=D.segs[si];let p=s[7];if(rev)p=p.slice().reverse();dist+=s._len;const f=cls(s)===3;
  legs.push({p,f,s});
  if(f){if(!cur){cur={len:0,name:D.names[s[0]]||'unnamed road',sp:s[2],p:[]};stretches.push(cur)}cur.len+=s._len;cur.p.push(...p)}else cur=null}
 // turn-by-turn by street name
 const steps=[];for(const l of legs){const n=D.names[l.s[0]]||'unnamed road';const last=steps[steps.length-1];if(last&&last.n===n&&last.f===l.f)last.d+=l.s._len;else steps.push({n,d:l.s._len,f:l.f,sp:l.s[2]})}
 return {dist,stretches,legs,steps}}
window.popSet=f=>{if(inMX(window._pll))return;map.closePopup();setField(f,{ll:window._pll,label:lbl(window._pll)})};
const ft=m=>Math.round(m*3.281)+' ft',mi=m=>(m/1609.34).toFixed(1)+' mi';
let routing=false;async function route(){$('title').innerHTML='<span class="spin">🛺</span> Finding a cart-friendly route…';$('sub').textContent='';const P=0.06;await ensure(Math.min(start.lat,end.lat)-P,Math.min(start.lng,end.lng)-P,Math.max(start.lat,end.lat)+P,Math.max(start.lng,end.lng)+P);if(routeG)map.removeLayer(routeG);routeG=null;const [a,da,a2]=nearest(start),[b,db,b2]=nearest(end);
 await new Promise(r=>setTimeout(r,0));let parts=null;if(a!=null&&b!=null){for(const [x,y] of [[a,b],[a2,b],[a,b2],[a2,b2]]){parts=astar(x,y);if(parts)break}}$('acts').style.display='flex';
 if(!parts){$('title').innerHTML='🚫 No legal route';$('sub').innerHTML=risky?'Even allowing ≤300 ft stretches on faster roads, there’s no way through.':(RULE.designated_only?'Every way there leaves the cart paths/designated roads.':`Every way there uses a ${RULE.max_posted+5}+ mph road.`)+' Try <b>⚠️ Risky</b> mode to see short-stretch options.';$('steps').innerHTML='';setSnap('half');return null}
 const r=summarize(parts);routeG=L.layerGroup().addTo(map);
 const all=[];r.legs.forEach(l=>all.push(...l.p));
 L.polyline(all.map(p=>[p[1],p[0]]),{color:'#fff',weight:10,opacity:.9,renderer,interactive:false}).addTo(routeG);
 L.polyline(all.map(p=>[p[1],p[0]]),{color:'#1d6fe0',weight:6,renderer,interactive:false}).addTo(routeG);
 r.stretches.forEach(s=>L.polyline(s.p.map(p=>[p[1],p[0]]),{color:'#ffc400',weight:8,renderer}).addTo(routeG).bindTooltip(`Risky: ${ft(s.len)} on ${s.name}`));
 const min=Math.max(1,Math.round(r.dist/1609.34/22*60));
 $('title').innerHTML=r.stretches.length?`⚠️ ${min} min · ${mi(r.dist)}`:`🛺 ${min} min · ${mi(r.dist)}`;
 $('sub').innerHTML=r.stretches.length?`Includes <b>${r.stretches.length}</b> risky stretch${r.stretches.length>1?'es':''} (${r.stretches.map(s=>ft(s.len)).join(', ')}) on faster roads.`:(RULE.designated_only?'All on cart paths & designated roads 🌴':`All on roads ≤${RULE.max_posted} mph 🌴`)+ruleNotes()+(da>150||db>150?' · snapped to nearest legal road':'');
 $('steps').innerHTML=r.steps.filter(s=>s.d>15).map(s=>`<div class="st"><span class="badge ${s.f?'y':''}">${s.f?ft(s.d):mi(s.d)}</span><span>${s.f?'⚠️ Risky: ':''}${s.n}${s.f&&s.sp&&s.sp!=99?` (${s.sp} mph)`:''}</span></div>`).join('');
 setSnap('half');focusStart();window.lastRoute={mi:+(r.dist/1609.34).toFixed(2),min,risky:r.stretches.map(s=>({road:s.name,ft:Math.round(s.len*3.281)}))};return r}
// center the START point (z16) inside the map area left visible by the top card and the sheet/desktop card
function focusStart(){if(!start)return;const sz=map.getSize(),Z=16,top=$('top').getBoundingClientRect(),sh=$('sheet').getBoundingClientRect();
 let x0=0,x1=sz.x,y0=top.bottom,y1=sz.y;
 if(DESK())x0=Math.max(top.right,sh.right);else y1=Math.min(sz.y,sh.top);
 if(y1-y0<80){y0=0;y1=sz.y}
 const want=L.point((x0+x1)/2,(y0+y1)/2),off=want.subtract(sz.divideBy(2));
 const c=map.unproject(map.project(start,Z).subtract(off),Z);window._focus={x:want.x,y:want.y};map.flyTo(c,Z,{duration:0.8})}
window.focusStart=focusStart;
const pinIcon=(c,e)=>L.divIcon({className:'',html:`<div class="pin" style="background:${c}"><span>${e}</span></div>`,iconSize:[30,30],iconAnchor:[15,30]});
// ---- route state: From/To fields (Google-Maps style). A point is {ll,label,me}; me=true means live GPS ("Your location").
let from=null,to=null,active=null; // active: field that the next map tap fills ('from'|'to'|null)
const P=x=>x?(x.me?myLL:x.ll):null;
const lbl=ll=>'Dropped pin · '+ll.lat.toFixed(4)+', '+ll.lng.toFixed(4);
function sync(){start=P(from);end=P(to);mk.forEach(m=>map.removeLayer(m));mk=[];
 // GPS point uses the live blue dot as its marker; a ring marks which end it is
 for(const [x,c,e] of [[from,'#14b8c4','🏠'],[to,'#ff7a59','🏖️']]){if(!x||!P(x))continue;
  mk.push(x.me?L.circleMarker(P(x),{radius:14,color:c,weight:3,fill:false,interactive:false,renderer}).addTo(map):L.marker(x.ll,{icon:pinIcon(c,e)}).addTo(map))}
 $('qf').value=from?(from.me?'Your location':from.label):'';$('q').value=to?(to.me?'Your location':to.label):'';
 $('xf').style.visibility=from?'visible':'hidden';$('xt').style.visibility=to?'visible':'hidden';
 $('fF').classList.toggle('act',active==='from');$('fT').classList.toggle('act',active==='to');
 $('reset').style.display=$('acts').style.display=(from||to)?'':'none';
 $('help').textContent=active==='from'?'Tip: tap the map to drop your start pin':active==='to'||(from&&!to)?'Tip: tap the map to drop a pin for your destination':(from&&to)?'Tip: tap any road for its speed & length':'Tip: tap the map twice (start, then destination), or tap a road for its speed & length';
 if(routeG&&!(start&&end)){map.removeLayer(routeG);routeG=null;$('steps').innerHTML=''}
 if(!(from||to)){$('title').innerHTML='🏖️ Golf Cart Maps';$('sub').innerHTML='Tap a road to see its speed limit and length, or plan a route above.'}
 else if(!(start&&end)){$('title').innerHTML=from?'📍 Start set':'🏖️ Destination set';$('sub').textContent=from?'Now pick where you’re headed.':'Now pick a start, or hit 📍 to start from you.'}}
function setField(f,pt){if(f==='from')from=pt;else to=pt;active=null;sync();if(start&&end)route();window.state=st()}
const st=()=>({from:from&&{label:$('qf').value,me:!!from.me,lat:P(from)&&P(from).lat},to:to&&{label:$('q').value,me:!!to.me,lat:P(to)&&P(to).lat},routed:!!routeG});
window.getState=st;
// a tap places a point: focused field first, else the first empty field. Returns false if nothing to fill.
const inPoly=(x,y,P)=>{let c=false;for(let i=0,j=P.length-1;i<P.length;j=i++){const [x1,y1]=P[i],[x2,y2]=P[j];if((y1>y)!==(y2>y)&&x<(x2-x1)*(y-y1)/(y2-y1)+x1)c=!c}return c};
const inMX=ll=>(REG&&REG.id==='sd'&&ll.lat<32.5343+(ll.lng+117.1235)*0.0367-0.0002)||!!(D&&D.meta.poly&&!inPoly(ll.lng,ll.lat,D.meta.poly));window.inMX=inMX;
function setPt(ll,label){if(inMX(ll)){$('help').textContent='⚠️ That spot is outside the map — '+(REG&&REG.cover||'pick another area in the city menu above.');return true}const f=active||(!from?'from':!to?'to':null);if(!f)return false;setField(f,{ll,label:label||lbl(ll)});return true}
function clearField(f){if(f==='from')from=null;else to=null;active=f;sync();window.state=st()}
function clearR(){from=to=null;active=null;if(routeG)map.removeLayer(routeG);routeG=null;$('steps').innerHTML='';map.closePopup();sync();window.state=st()}
window.resetRoute=clearR;
map.on('click',e=>{if(!setPt(e.latlng))map.closePopup()});$('clr').onclick=clearR;$('reset').onclick=clearR;
function swap(){[from,to]=[to,from];active=null;sync();if(start&&end)route();else if(routeG){map.removeLayer(routeG);routeG=null}window.state=st()}
$('swap').onclick=swap;$('swap2').onclick=swap;window.swapRoute=swap;
for(const [f,id,x] of [['from','qf','xf'],['to','q','xt']]){
 $(id).addEventListener('focus',()=>{active=f;$(id).select();sync();curField=f});
 $(id).addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();clearField(f);$(id).value='';$('sugg').style.display='none'}});
 $(x).onclick=e=>{e.preventDefault();clearField(f);$('sugg').style.display='none'}}
let curField='to';
function setRisky(v){risky=v;$('cRisk').classList.toggle('on',v);$('cNorm').classList.toggle('on',!v);if(start&&end)route()}
window.setRisky=setRisky;
$('cNorm').onclick=()=>setRisky(false);$('cRisk').onclick=()=>setRisky(true);

let me,meAcc,myLL=null,watching=false;
function locate(){if(!navigator.geolocation){$('sub').textContent='Location not supported on this device.';return}
 $('showloc').textContent='📍 Finding you…';let first=true;
 const ok=p=>{myLL=L.latLng(p.coords.latitude,p.coords.longitude);const acc=p.coords.accuracy;
  if(!me){meAcc=L.circle(myLL,{radius:acc,color:'#1d6fe0',weight:1,fillColor:'#1d6fe0',fillOpacity:.12,interactive:false,renderer}).addTo(map);me=L.circleMarker(myLL,{radius:8,color:'#fff',fillColor:'#1d6fe0',fillOpacity:1,weight:3,interactive:false,renderer}).addTo(map)}
  else{me.setLatLng(myLL);meAcc.setLatLng(myLL).setRadius(acc)}
  if(first){first=false;const rg=regionAt(myLL.lat,myLL.lng);if(rg&&REG&&rg.id!==REG.id){loadRegion(rg.id,true)}map.setView(myLL,16);$('showloc').style.display='none';if(to&&to.me){sync();if(start&&end)route()}else setField('from',{me:true})}else if((from&&from.me)||(to&&to.me)){sync()}};
 const err=e=>{$('showloc').textContent='📍 Show my location';$('sub').textContent=e.code===1?'Location is blocked. Turn it on in Settings › Safari › Location.':'Couldn’t find you: '+e.message};
 if(watching){navigator.geolocation.getCurrentPosition(p=>{first=true;ok(p)},err,{enableHighAccuracy:true});return}
 watching=true;navigator.geolocation.watchPosition(ok,err,{enableHighAccuracy:true,maximumAge:5000})}
$('loc').onclick=locate;$('showloc').onclick=locate;$('useme').onmousedown=e=>e.preventDefault();$('useme').onclick=()=>{$('sugg').style.display='none';if(myLL)setField(active||'from',{me:true});else{active=null;locate()}};window.fakeLocate=(lat,lng)=>{myLL=L.latLng(lat,lng);if(!me){me=L.circleMarker(myLL,{radius:8,color:'#fff',fillColor:'#1d6fe0',fillOpacity:1,weight:3,interactive:false,renderer}).addTo(map)}setField('from',{me:true})};
// ---- fast search: local index (instant) + Photon autocomplete + Nominatim fallback ----
const qcache=new Map();let POIS=[],nameAt=null,qseq=0,tmr;

const norm=t=>t.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9 ]/g,' ').replace(/\s+/g,' ').trim();
function streetIndex(){nameAt=new Map();for(const s of D.segs){if(!nameAt.has(s[0])){const p=s[7][0];nameAt.set(s[0],[p[0],p[1]])}}}
function localMatches(q){const n=norm(q);if(!n)return[];const out=[];
 for(const p of POIS){const pn=norm(p[0]);if(pn.includes(n))out.push({name:p[0],sub:(p[1]||'place').replace('_',' ')+(p[4]?' · '+p[4]:''),lat:p[3],lon:p[2],score:pn.startsWith(n)?0:1})}
 if(!nameAt||nameAt.size<D.segs.length/50)streetIndex();
 D.names.forEach((nm,i)=>{if(!nm)return;const pn=norm(nm);if(pn.startsWith(n)||pn.includes(' '+n)){const c=nameAt.get(i);if(c)out.push({name:nm,sub:'street',lat:c[1],lon:c[0],score:pn.startsWith(n)?0.5:1.5})}});
 return out.sort((a,b)=>a.score-b.score).slice(0,5)}
async function remote(q){const key=(REG?REG.id:'')+'|'+norm(q);if(qcache.has(key))return qcache.get(key);const b=D.meta.bbox,c=map.getCenter();let res=[];
 try{const ac=new AbortController();const to=setTimeout(()=>ac.abort(),2500);
  const r=await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(q)}&limit=6&lat=${c.lat}&lon=${c.lng}&bbox=${b[1]},${b[0]},${b[3]},${b[2]}`,{signal:ac.signal});clearTimeout(to);
  const j=await r.json();res=j.features.map(f=>{const p=f.properties;return{name:p.name||[p.housenumber,p.street].filter(Boolean).join(' '),sub:[p.housenumber&&p.name?p.street:null,p.city||p.district,p.osm_value].filter(Boolean).join(' · '),lat:f.geometry.coordinates[1],lon:f.geometry.coordinates[0]}}).filter(x=>x.name)}
 catch(e){try{const r=await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=5&bounded=1&viewbox=${b[1]},${b[2]},${b[3]},${b[0]}&q=${encodeURIComponent(q)}`);const j=await r.json();res=j.map(x=>({name:x.display_name.split(',')[0],sub:x.display_name.split(',').slice(1,3).join(','),lat:+x.lat,lon:+x.lon}))}catch(_){}}
 qcache.set(key,res);return res}
function showSugg(list){list=list.filter(x=>!inMX(L.latLng(x.lat,x.lon)));const sg=$('sugg');sg.innerHTML='';sg.style.display=list.length?'block':'none';
 list.forEach(x=>{const d=document.createElement('div');d.innerHTML=`<b>${x.name}</b><br><small style="color:#6b8592">${x.sub||''}</small>`;d.onclick=()=>pick(x);sg.appendChild(d)})}
function pick(x){$('sugg').style.display='none';document.activeElement&&document.activeElement.blur();const ll=L.latLng(x.lat,x.lon);map.setView(ll,16);active=curField;setPt(ll,x.name)}
const spin=v=>$('qspin').style.display=v?'inline-block':'none';
const onq=e=>{clearTimeout(tmr);const v=e.target.value.trim();if(v.length<2){$('sugg').style.display='none';spin(false);return}
 const loc=D?localMatches(v):[];showSugg(loc);
 if(v.length<3)return;spin(true);const my=++qseq;
 tmr=setTimeout(async()=>{const r=await remote(v);if(my!==qseq)return;spin(false);
  const seen=new Set(loc.map(x=>norm(x.name)));showSugg([...loc,...r.filter(x=>{const k=norm(x.name);if(seen.has(k))return false;seen.add(k);return true})].slice(0,7))},250)};
$('q').oninput=onq;$('qf').oninput=onq;for(const id of ['q','qf'])$(id).addEventListener('keydown',e=>{if(e.key==='Enter'){const f=$('sugg').firstChild;if(f)f.click()}});
window.testRoute=async(a,b,rk=false)=>{risky=rk;from={ll:L.latLng(a),label:'A'};to={ll:L.latLng(b),label:'B'};active=null;sync();if(inMX(from.ll)||inMX(to.ll))return null;const r=await route();return r?window.lastRoute:null};
let readyRes,READY=new Promise(r=>readyRes=r);
// ---- regions: ?r= / saved > geolocation (already-granted only) nearest within 50 mi > San Diego ----
const modeName=()=>MODE==='lsv'?'LSV':'golf cart';
function ruleNotes(){const n=[];if(RULE.radius_mi)n.push(`stay within ${RULE.radius_mi} mi of where the cart is registered`);if(RULE.daylight_only)n.push('daylight only');return n.length?' · '+n.join(' · '):''}
function setRule(){const st=RULES[REG.state]||RULES.CA;RULE={...(st[MODE]||st.lsv)};const rr=REG.rules&&REG.rules[MODE];if(rr)Object.assign(RULE,rr);
 $('cMode').textContent=MODE==='lsv'?'🚙 LSV':'⛳ Golf cart';$('rnote').textContent=`${st.name} ${modeName()}: `+(RULE.designated_only?`cart paths + designated roads${RULE.assume?' (local streets, unverified)':''}`:`roads posted ≤${RULE.max_posted} mph`)+ruleNotes();$('rnote').title=RULE.cite||''}
function regionAt(lat,lng){let best=null,bd=80467;for(const r of REGIONS){const b=r.bbox;if(lat>=b[0]&&lat<=b[2]&&lng>=b[1]&&lng<=b[3])return r;const d=hav([lng,lat],[r.center[1],r.center[0]]);if(d<bd){bd=d;best=r}}return best}
function resetData(){if(layer){layer.clearLayers();map.removeLayer(layer)}shown={};buckets={};nodes={};adj={};fast=new Set();fnode=new Set();cnode=new Set();loaded.clear();for(const k in loading)delete loading[k];nameAt=null;POIS=[];D=null;window.ready=false;READY=new Promise(r=>readyRes=r)}
async function loadRegion(id,keepView){const r=REGIONS.find(x=>x.id===id)||REGIONS[0];if(REG&&REG.id===r.id&&D)return;if(!keepView)clearR();resetData();REG=r;BASE='data/'+r.id+'/';window.REG=r;
 try{localStorage.setItem('gcm-region',r.id)}catch(_){}$('city').value=r.id;setRule();$('sub').textContent='Loading roads…';
 if(!keepView)map.setView(r.center,r.zoom);
 fetch(BASE+'pois.json').then(x=>x.ok?x.json():[]).then(j=>{if(REG===r)POIS=j}).catch(()=>{});
 const j=await (await fetch(BASE+'index.json')).json();if(REG!==r)return;$('lgCart').style.display=j.meta.stats&&j.meta.stats.cartpath?'':'none';D={...j,segs:[],tileSet:new Set(j.meta.tiles)};readyRes();
 $('dmeta').textContent=`Data: OSM ${j.meta.generated}.`;draw();if(!keepView)clearR();else sync();await onMove();window.ready=true}
window.loadRegion=loadRegion;
function setMode(m){MODE=m;try{localStorage.setItem('gcm-mode',m)}catch(_){}setRule();if(!D)return;adj={};nodes={};fast=new Set();fnode=new Set();cnode=new Set();buildGraph(0);shown={};layer.clearLayers();refresh();if(start&&end)route()}
window.setMode=setMode;
$('cMode').onclick=()=>setMode(MODE==='lsv'?'golf_cart':'lsv');
$('city').onchange=e=>loadRegion(e.target.value);
(async()=>{[REGIONS,RULES]=await Promise.all([fetch('data/regions.json').then(r=>r.json()),fetch('data/rules.json').then(r=>r.json())]);
 $('city').innerHTML=REGIONS.map(r=>`<option value="${r.id}">${r.short}${r.beta?' (beta)':''}</option>`).join('');
 const q=new URLSearchParams(location.search).get('r');let saved=null;try{saved=localStorage.getItem('gcm-region')}catch(_){}
 let id=(q&&REGIONS.some(r=>r.id===q))?q:(saved&&REGIONS.some(r=>r.id===saved))?saved:null;
 if(!id&&navigator.permissions&&navigator.geolocation){try{const p=await navigator.permissions.query({name:'geolocation'});if(p.state==='granted'){const pos=await new Promise((ok,no)=>navigator.geolocation.getCurrentPosition(ok,no,{timeout:4000,maximumAge:600000}));const r=regionAt(pos.coords.latitude,pos.coords.longitude);if(r)id=r.id}}catch(_){}}
 await loadRegion(id||'sd')})();

// ---- bottom sheet: pointer-driven, translateY snapping ----
const sheet=$('sheet'),shead=$('shead');let snap='full';
function vh(){return window.innerHeight}
const DESK=()=>matchMedia('(min-width:900px)').matches;
function sizeSheet(){sheet.style.height=DESK()?'':Math.round(vh()*0.85)+'px'}
function snaps(){const H=sheet.offsetHeight,c=Math.max(0,H-shead.offsetHeight-6);if(DESK())return{full:0,half:0,collapsed:c};return{full:0,half:Math.max(0,H-vh()*0.35),collapsed:c}}
let curY=0;
function place(y){curY=y;sheet.style.transform=`translate3d(0,${y}px,0)`;const vis=sheet.offsetHeight-y;
 $('loc').style.bottom=DESK()?'24px':(vis+14)+'px';$('chev').textContent=snap==='collapsed'?'⌃':'⌄'}
function setSnap(n){snap=n;place(snaps()[n])}
window.setSnap=setSnap;window.getSnap=()=>snap;
const ORDER=['collapsed','half','full'];
let drag=null;
function ds(y,id){drag={y0:y,t0:Date.now(),start:curY,moved:false,id};sheet.classList.add('drag')}
function dm(y){if(!drag)return;const d=y-drag.y0;if(Math.abs(d)>6)drag.moved=true;const S=snaps();place(Math.min(S.collapsed,Math.max(0,drag.start+d)))}
function de(y){if(!drag)return;const d=y-drag.y0,v=d/Math.max(1,Date.now()-drag.t0),moved=drag.moved;drag=null;sheet.classList.remove('drag');
 if(!moved){setSnap(ORDER[(ORDER.indexOf(snap)+1)%3]);return}
 const S=snaps();let best=Object.keys(S).reduce((a,b)=>Math.abs(S[a]-curY)<Math.abs(S[b]-curY)?a:b);
 if(best===snap&&Math.abs(v)>0.3){const i=ORDER.indexOf(snap)+(v>0?-1:1);best=ORDER[Math.max(0,Math.min(2,i))]}setSnap(best)}
const isBtn=e=>e.target.closest&&e.target.closest('#chev');
if(window.PointerEvent){
 shead.addEventListener('pointerdown',e=>{if(isBtn(e))return;e.preventDefault();try{shead.setPointerCapture(e.pointerId)}catch(_){}ds(e.clientY,e.pointerId)},{passive:false});
 shead.addEventListener('pointermove',e=>{if(drag){e.preventDefault();dm(e.clientY)}},{passive:false});
 shead.addEventListener('pointerup',e=>{if(drag){e.preventDefault();de(e.clientY)}},{passive:false});
 shead.addEventListener('pointercancel',e=>{if(drag)de(e.clientY)});
}
// touch fallback: just block native scroll/bounce on header
shead.addEventListener('touchstart',e=>{if(!isBtn(e))e.preventDefault()},{passive:false});
shead.addEventListener('touchmove',e=>e.preventDefault(),{passive:false});
$('chev').addEventListener('click',e=>{e.stopPropagation();setSnap(snap==='collapsed'?'half':'collapsed')});
L.DomEvent.disableClickPropagation(sheet);L.DomEvent.disableScrollPropagation(sheet);
map.on('click',()=>{if(!routeG&&!from&&snap!=='collapsed')setSnap('collapsed')});
addEventListener('resize',()=>{sizeSheet();setSnap(snap)});
sizeSheet();sheet.style.transition='none';setSnap('half');requestAnimationFrame(()=>requestAnimationFrame(()=>sheet.style.transition=''));
