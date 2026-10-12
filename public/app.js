const map=L.map('map',{preferCanvas:true,zoomControl:false,attributionControl:true}).setView([32.84,-117.27],14);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);
const renderer=L.canvas({tolerance:8});
const $=id=>document.getElementById(id);
const RISKY_MAX=91.44; // 300 ft
let D,risky=false,layer,nodes={},adj={},start=null,end=null,routeG=null,mk=[];
// cls: 0 posted ok, 1 assumed ok, 3 forbidden (posted >=40 or untagged major)
const cls=s=>(s[2]==null||s[2]>35)?3:(s[3]==='t'?0:1);
const STY=[{color:'#12a150',weight:3.2},{color:'#4cc38a',weight:2.6,dashArray:'5 4'},null,{color:'#e5484d',weight:3,opacity:.75}];
const MAJOR=new Set(['motorway','motorway_link','trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link']);
let buckets={},shown={};const G=0.02;
function bucketize(from){D.segs.slice(from).forEach((s,j)=>{const i=from+j;const p=s[7][0],k=Math.floor(p[0]/G)+','+Math.floor(p[1]/G);(buckets[k]||(buckets[k]=[])).push(i)})}
function draw(){layer=L.layerGroup().addTo(map);refresh()}
function refresh(){const b=map.getBounds().pad(0.2),z=map.getZoom(),minor=z>=14;
 const x0=Math.floor(b.getWest()/G),x1=Math.floor(b.getEast()/G),y0=Math.floor(b.getSouth()/G),y1=Math.floor(b.getNorth()/G),want={};
 for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){const k=x+','+y;if(buckets[k])want[k+(minor?'m':'')]=k}
 for(const k in shown)if(!(k in want)){layer.removeLayer(shown[k]);delete shown[k]}
 for(const k in want)if(!shown[k]){const g=L.layerGroup();for(const i of buckets[want[k]]){const s=D.segs[i];if(!minor&&!MAJOR.has(s[1]))continue;g.addLayer(mkLine(s))}shown[k]=g;layer.addLayer(g)}}
const loaded=new Set(),loading={};
async function loadTile(k){if(loaded.has(k))return;if(!loading[k])loading[k]=fetch('data/tiles/'+k+'.json').then(r=>r.json()).then(segs=>{if(loaded.has(k))return;loaded.add(k);const from=D.segs.length;D.segs.push(...segs);bucketize(from);buildGraph(from)});return loading[k]}
function tilesIn(s,w,n,e){const T=D.meta.tileSize,out=[];for(let x=Math.floor(w/T);x<=Math.floor(e/T);x++)for(let y=Math.floor(s/T);y<=Math.floor(n/T);y++){const k=x+'_'+y;if(D.tileSet.has(k))out.push(k)}return out}
async function ensure(s,w,n,e){const ks=tilesIn(s,w,n,e).filter(k=>!loaded.has(k));if(!ks.length)return;let done=0;const msg=()=>{$('sub').textContent=`Loading roads… ${done}/${ks.length} areas`};const prev=$('sub').innerHTML;msg();await Promise.all(ks.map(k=>loadTile(k).then(()=>{done++;msg()})));$('sub').innerHTML=window.ready?prev:'Tap the map to set a start, or hit 📍.'}
async function onMove(){if(!D)return;const b=map.getBounds().pad(0.1);const n0=loaded.size;if(map.getZoom()>=11)await ensure(b.getSouth(),b.getWest(),b.getNorth(),b.getEast());if(loaded.size!==n0){shown={};layer.clearLayers()}refresh()}
map.on('moveend',onMove);
function mkLine(s){const c=cls(s);const pl=L.polyline(s[7].map(p=>[p[1],p[0]]),{...STY[c],renderer});
 pl.on('click',e=>{L.DomEvent.stopPropagation(e);const sp=s[2];
  L.popup().setLatLng(e.latlng).setContent(`<b>${D.names[s[0]]||'(unnamed road)'}</b><br>${s[1].replace('_',' ')} · ${sp==null||sp==99?'no limit recorded':sp+' mph'}${s[3]==='t'?'':' (assumed)'}<br><b style="color:${c===3?'#e5484d':'#12a150'}">${c===3?'Avoid: 40+ mph or major road':'OK for LSV'}</b>`).openOn(map)});return pl}
function hav(a,b){const R=6371000,r=Math.PI/180,dl=(b[1]-a[1])*r,dn=(b[0]-a[0])*r,x=Math.sin(dl/2)**2+Math.cos(a[1]*r)*Math.cos(b[1]*r)*Math.sin(dn/2)**2;return 2*R*Math.asin(Math.sqrt(x))}
function len(p){let l=0;for(let i=1;i<p.length;i++)l+=hav(p[i-1],p[i]);return l}
let fast=new Set();
function buildGraph(from){D.segs.slice(from).forEach((s,j)=>{const i=from+j;const c=cls(s),a=s[5],b=s[6],p=s[7];s._len??=len(p);nodes[a]=p[0];nodes[b]=p[p.length-1];
  if(s[3]==='t'&&s[2]>=40){fast.add(a);fast.add(b)}
  const f=c===3;
  if(s[4]>=0)(adj[a]||(adj[a]=[])).push([b,s._len,i,false,f]);if(s[4]<=0)(adj[b]||(adj[b]=[])).push([a,s._len,i,true,f])})}
function nearest(ll){let best=null,bd=1e18;const q=[ll.lng,ll.lat];for(const k in nodes){if(!(adj[k]||[]).some(e=>!e[4]))continue;const d=hav(q,nodes[k]);if(d<bd){bd=d;best=+k}}return [best,bd]}
// A* over (node, metres-of-current-forbidden-run). Legal mode: forbidden edges never used.
// Crossing a forbidden road = passing through a shared node between two allowed edges (CVC 21260(b)(1)).
function astar(s,t){const key=(n,r)=>n+'|'+Math.round(r);const T=nodes[t];const g=new Map(),prev=new Map();const k0=key(s,0);g.set(k0,0);
 const h=[[hav(nodes[s],T),s,0,k0]],done=new Set();
 const push=x=>{h.push(x);let i=h.length-1;while(i>0){const p=(i-1)>>1;if(h[p][0]<=h[i][0])break;[h[p],h[i]]=[h[i],h[p]];i=p}};
 const pop=()=>{const top=h[0],l=h.pop();if(h.length){h[0]=l;let i=0;for(;;){let a=2*i+1,b=a+1,m=i;if(a<h.length&&h[a][0]<h[m][0])m=a;if(b<h.length&&h[b][0]<h[m][0])m=b;if(m===i)break;[h[m],h[i]]=[h[i],h[m]];i=m}}return top};
 let goal=null;
 while(h.length){const [,u,run,ku]=pop();if(done.has(ku))continue;done.add(ku);if(u===t&&run===0){goal=ku;break}
  for(const [v,w,si,rev,f] of adj[u]||[]){let nr,cost=w;
   if(f){if(!risky)continue;nr=run+w;if(nr>RISKY_MAX)continue;cost=w*6+60}else{nr=0;if(fast.has(v))cost+=150}
   const kv=key(v,nr),ng=g.get(ku)+cost;if(!g.has(kv)||ng<g.get(kv)){g.set(kv,ng);prev.set(kv,[ku,si,rev]);push([ng+hav(nodes[v],T),v,nr,kv])}}}
 if(!goal)return null;const parts=[];let x=goal;while(x!==k0){const [pk,si,rev]=prev.get(x);parts.push([si,rev]);x=pk}parts.reverse();return parts}
function summarize(parts){let dist=0,stretches=[],cur=null,line=[];const legs=[];
 for(const [si,rev] of parts){const s=D.segs[si];let p=s[7];if(rev)p=p.slice().reverse();dist+=s._len;const f=cls(s)===3;
  legs.push({p,f,s});
  if(f){if(!cur){cur={len:0,name:D.names[s[0]]||'unnamed road',sp:s[2],p:[]};stretches.push(cur)}cur.len+=s._len;cur.p.push(...p)}else cur=null}
 // turn-by-turn by street name
 const steps=[];for(const l of legs){const n=D.names[l.s[0]]||'unnamed road';const last=steps[steps.length-1];if(last&&last.n===n&&last.f===l.f)last.d+=l.s._len;else steps.push({n,d:l.s._len,f:l.f,sp:l.s[2]})}
 return {dist,stretches,legs,steps}}
const ft=m=>Math.round(m*3.281)+' ft',mi=m=>(m/1609.34).toFixed(1)+' mi';
async function route(){const P=0.06;await ensure(Math.min(start.lat,end.lat)-P,Math.min(start.lng,end.lng)-P,Math.max(start.lat,end.lat)+P,Math.max(start.lng,end.lng)+P);if(routeG)map.removeLayer(routeG);routeG=null;const [a,da]=nearest(start),[b,db]=nearest(end);
 const parts=a!=null&&b!=null?astar(a,b):null;$('acts').style.display='flex';
 if(!parts){$('title').innerHTML='🚫 No legal route';$('sub').innerHTML=risky?'Even allowing ≤300 ft stretches on faster roads, there’s no way through.':'Every way there uses a 40+ mph road. Try <b>⚠️ Risky</b> mode to see short-stretch options.';$('steps').innerHTML='';setSnap('collapsed');setSnap('collapsed');return null}
 const r=summarize(parts);routeG=L.layerGroup().addTo(map);
 const all=[];r.legs.forEach(l=>all.push(...l.p));
 L.polyline(all.map(p=>[p[1],p[0]]),{color:'#fff',weight:10,opacity:.9}).addTo(routeG);
 L.polyline(all.map(p=>[p[1],p[0]]),{color:'#1d6fe0',weight:6}).addTo(routeG);
 r.stretches.forEach(s=>L.polyline(s.p.map(p=>[p[1],p[0]]),{color:'#ffc400',weight:8}).addTo(routeG).bindTooltip(`Risky: ${ft(s.len)} on ${s.name}`));
 const min=Math.max(1,Math.round(r.dist/1609.34/22*60));
 $('title').innerHTML=r.stretches.length?`⚠️ ${min} min · ${mi(r.dist)}`:`🛺 ${min} min · ${mi(r.dist)}`;
 $('sub').innerHTML=r.stretches.length?`Includes <b>${r.stretches.length}</b> risky stretch${r.stretches.length>1?'es':''} (${r.stretches.map(s=>ft(s.len)).join(', ')}) on faster roads.`:'All on roads ≤35 mph 🌴'+(da>150||db>150?' · snapped to nearest legal road':'');
 $('steps').innerHTML=r.steps.filter(s=>s.d>15).map(s=>`<div class="st"><span class="badge ${s.f?'y':''}">${s.f?ft(s.d):mi(s.d)}</span><span>${s.f?'⚠️ Risky: ':''}${s.n}${s.f&&s.sp&&s.sp!=99?` (${s.sp} mph)`:''}</span></div>`).join('');
 setSnap('half');window.lastRoute={mi:+(r.dist/1609.34).toFixed(2),min,risky:r.stretches.map(s=>({road:s.name,ft:Math.round(s.len*3.281)}))};return r}
const pinIcon=(c,e)=>L.divIcon({className:'',html:`<div class="pin" style="background:${c}"><span>${e}</span></div>`,iconSize:[30,30],iconAnchor:[15,30]});
function setPt(ll){if(!start||end){clearR();start=ll;mk.push(L.marker(ll,{icon:pinIcon('#14b8c4','🏠')}).addTo(map));$('title').innerHTML='📍 Start set';$('sub').textContent='Tap the map or search for where you’re headed.'}
 else{end=ll;mk.push(L.marker(ll,{icon:pinIcon('#ff7a59','🏖️')}).addTo(map));route()}}
function clearR(){start=end=null;mk.forEach(m=>map.removeLayer(m));mk=[];if(routeG)map.removeLayer(routeG);routeG=null;$('steps').innerHTML='';$('acts').style.display='none';$('title').innerHTML='🏖️ Golf Cart Maps';$('sub').textContent='Tap the map to set a start, or hit 📍.'}
map.on('click',e=>setPt(e.latlng));$('clr').onclick=clearR;
$('swap').onclick=()=>{if(start&&end){const a=end,b=start;clearR();setPt(a);setPt(b)}};
function setRisky(v){risky=v;$('cRisk').classList.toggle('on',v);$('cNorm').classList.toggle('on',!v);if(start&&end)route()}
$('cNorm').onclick=()=>setRisky(false);$('cRisk').onclick=()=>setRisky(true);
let legendOn=true;$('lay').onclick=()=>{legendOn=!legendOn;$('legend').style.display=$('disc').style.display=legendOn?'':'none'};
let me;$('loc').onclick=()=>navigator.geolocation.getCurrentPosition(p=>{const ll=L.latLng(p.coords.latitude,p.coords.longitude);
 if(me)map.removeLayer(me);me=L.circleMarker(ll,{radius:8,color:'#fff',fillColor:'#1d6fe0',fillOpacity:1,weight:3}).addTo(map);map.setView(ll,16);clearR();start=ll;
 mk.push(L.marker(ll,{icon:pinIcon('#14b8c4','🛺')}).addTo(map));$('title').innerHTML='📍 Starting from you';$('sub').textContent='Tap or search a destination.'},e=>{$('sub').textContent='Location unavailable: '+e.message},{enableHighAccuracy:true});
let tmr,lastQ=0;$('q').oninput=e=>{clearTimeout(tmr);const v=e.target.value.trim();if(v.length<4){$('sugg').style.display='none';return}
 tmr=setTimeout(async()=>{await new Promise(r=>setTimeout(r,Math.max(0,1100-(Date.now()-lastQ))));lastQ=Date.now();const b=D.meta.bbox;
  const j=await (await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=5&bounded=1&viewbox=${b[1]},${b[2]},${b[3]},${b[0]}&q=${encodeURIComponent(v)}`)).json();
  const sg=$('sugg');sg.innerHTML='';sg.style.display=j.length?'block':'none';
  j.forEach(x=>{const d=document.createElement('div');d.textContent='📍 '+x.display_name.split(',').slice(0,3).join(',');d.onclick=()=>{sg.style.display='none';$('q').value=x.display_name.split(',')[0];$('q').blur();
   const ll=L.latLng(+x.lat,+x.lon);map.setView(ll,15);if(start&&end){const s=start;clearR();setPt(s)}setPt(ll)};sg.appendChild(d)})},700)};
window.testRoute=async(a,b,rk=false)=>{risky=rk;clearR();start=L.latLng(a);mk.push(L.marker(start,{icon:pinIcon('#14b8c4','🏠')}).addTo(map));end=L.latLng(b);mk.push(L.marker(end,{icon:pinIcon('#ff7a59','🏖️')}).addTo(map));const r=await route();return r?window.lastRoute:null};
fetch('data/index.json').then(r=>r.json()).then(async j=>{D={...j,segs:[],tileSet:new Set(j.meta.tiles)};$('dmeta').textContent=`Data: OSM ${j.meta.generated}.`;draw();clearR();await onMove();window.ready=true});

// ---- bottom sheet: collapsed / half / full with touch drag ----
const sheet=$('sheet'),shead=$('shead');let snap='collapsed';
function sab(){return parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--sab'))||0}
function snaps(){const H=sheet.offsetHeight,vh=window.innerHeight;return{collapsed:H-(shead.offsetHeight+sab()+6),half:H-vh*0.45,full:0}}
function place(y){sheet.style.transform=`translateY(${y}px)`;const vis=sheet.offsetHeight-y;$('loc').style.bottom=(vis+14)+'px';$('lay').style.bottom=(vis+74)+'px';const hide=vis>window.innerHeight*0.6;$('loc').style.opacity=$('lay').style.opacity=hide?0:1;$('loc').style.pointerEvents=$('lay').style.pointerEvents=hide?'none':''}
function setSnap(n){snap=n;place(snaps()[n])}
window.setSnap=setSnap;window.getSnap=()=>snap;
let dy0=null,y0=0,moved=false,t0=0;
const cur=()=>{const m=/translateY\(([-\d.]+)px/.exec(sheet.style.transform);return m?+m[1]:0};
function ds(y){dy0=y;y0=cur();moved=false;t0=Date.now();sheet.classList.add('drag')}
function dm(y){if(dy0==null)return;const d=y-dy0;if(Math.abs(d)>4)moved=true;const S=snaps();place(Math.min(S.collapsed,Math.max(0,y0+d)))}
function de(y){if(dy0==null)return;sheet.classList.remove('drag');const d=y-dy0,S=snaps();dy0=null;
 if(!moved){setSnap(snap==='collapsed'?'half':'collapsed');return}
 const v=d/Math.max(1,Date.now()-t0),y1=cur();let best;
 best=Object.keys(S).reduce((a,b)=>Math.abs(S[a]-y1)<Math.abs(S[b]-y1)?a:b);
 if(best===snap&&Math.abs(v)>0.4)best=v>0?(snap==='full'?'half':'collapsed'):(snap==='collapsed'?'half':'full');setSnap(best)}
shead.addEventListener('touchstart',e=>{e.preventDefault();ds(e.touches[0].clientY)},{passive:false});
shead.addEventListener('touchmove',e=>{e.preventDefault();dm(e.touches[0].clientY)},{passive:false});
shead.addEventListener('touchend',e=>{e.preventDefault();de(e.changedTouches[0].clientY)},{passive:false});
shead.addEventListener('mousedown',e=>{ds(e.clientY);const mm=ev=>dm(ev.clientY),mu=ev=>{de(ev.clientY);removeEventListener('mousemove',mm);removeEventListener('mouseup',mu)};addEventListener('mousemove',mm);addEventListener('mouseup',mu)});
L.DomEvent.disableClickPropagation(sheet);L.DomEvent.disableScrollPropagation(sheet);
addEventListener('resize',()=>setSnap(snap));
requestAnimationFrame(()=>{sheet.style.transition='none';setSnap('full');requestAnimationFrame(()=>sheet.style.transition='')});
