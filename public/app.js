const map=L.map('map',{preferCanvas:true,zoomControl:false}).setView([32.84,-117.27],13);
L.control.zoom({position:'bottomright'}).addTo(map);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,opacity:.6,attribution:'© OpenStreetMap contributors'}).addTo(map);
const renderer=L.canvas({tolerance:8});
let D,mode=35,allowUnk=false,layer,nodes={},adj={},start=null,end=null,routeLine,mk=[];
const $=id=>document.getElementById(id), st=t=>$('status').innerHTML=t;
// status: 0 allowed posted, 1 allowed inferred, 2 unknown, 3 forbidden
function cls(s){const sp=s[2],src=s[3];if(sp==null)return 2;if(sp>mode)return 3;return src==='t'?0:1}
const STY=[{color:'#1a9641',weight:3},{color:'#5cc45c',weight:2.5,dashArray:'5 3'},{color:'#f0a500',weight:3},{color:'#d7191c',weight:2.5,opacity:.7}];
function draw(){if(layer)map.removeLayer(layer);layer=L.layerGroup();
 for(const s of D.segs){const c=cls(s);const pl=L.polyline(s[7].map(p=>[p[1],p[0]]),{...STY[c],renderer});pl._s=s;
  pl.on('click',e=>{L.DomEvent.stopPropagation(e);const sp=s[2];const lbl=['Allowed (posted limit)','Allowed (limit inferred)','Unknown – speed limit not recorded','Not allowed'][cls(s)];
   L.popup().setLatLng(e.latlng).setContent(`<b>${D.names[s[0]]||'(unnamed)'}</b><br>Type: ${s[1]}<br>Speed: ${sp==null?'not tagged':sp==99?'not tagged (major road, assumed >35)':sp+' mph'}<br>Source: ${s[3]==='t'?'OSM maxspeed tag':sp==null?'—':'inferred from road type'}<br><b>${lbl}</b>`).openOn(map)});
  layer.addLayer(pl)}
 layer.addTo(map);buildGraph();if(start&&end)route()}
function hav(a,b){const R=6371000,r=Math.PI/180,dl=(b[1]-a[1])*r,dn=(b[0]-a[0])*r,x=Math.sin(dl/2)**2+Math.cos(a[1]*r)*Math.cos(b[1]*r)*Math.sin(dn/2)**2;return 2*R*Math.asin(Math.sqrt(x))}
function len(p){let l=0;for(let i=1;i<p.length;i++)l+=hav(p[i-1],p[i]);return l}
function buildGraph(){adj={};nodes={};
 D.segs.forEach((s,i)=>{const c=cls(s);if(c===3||(c===2&&!allowUnk))return;const a=s[5],b=s[6],p=s[7];
  nodes[a]=p[0];nodes[b]=p[p.length-1];const L_=s._len??(s._len=len(p));
  if(s[4]>=0)(adj[a]||(adj[a]=[])).push([b,L_,i,false]);if(s[4]<=0)(adj[b]||(adj[b]=[])).push([a,L_,i,true])})}
function nearest(ll){let best=null,bd=1e18;for(const k in nodes){if(!adj[k])continue;const d=hav([ll.lng,ll.lat],nodes[k]);if(d<bd){bd=d;best=k}}return [best,bd]}
// A* with binary heap
function astar(s,t){const g={[s]:0},prev={},T=nodes[t],h=[[hav(nodes[s],T),s]];const done=new Set();
 const push=x=>{h.push(x);let i=h.length-1;while(i>0){const p=(i-1)>>1;if(h[p][0]<=h[i][0])break;[h[p],h[i]]=[h[i],h[p]];i=p}};
 const pop=()=>{const top=h[0],l=h.pop();if(h.length){h[0]=l;let i=0;for(;;){let a=2*i+1,b=a+1,m=i;if(a<h.length&&h[a][0]<h[m][0])m=a;if(b<h.length&&h[b][0]<h[m][0])m=b;if(m===i)break;[h[m],h[i]]=[h[i],h[m]];i=m}}return top};
 while(h.length){const [,u]=pop();if(u==t)break;if(done.has(u))continue;done.add(u);
  for(const [v,w,si,rev] of adj[u]||[]){const ng=g[u]+w;if(g[v]===undefined||ng<g[v]){g[v]=ng;prev[v]=[u,si,rev];push([ng+hav(nodes[v],T),v])}}}
 if(g[t]===undefined)return null;const pts=[];let x=t;while(x!=s){const [u,si,rev]=prev[x];let p=D.segs[si][7];if(!rev)p=p.slice().reverse();pts.push(...p);x=u}
 return {dist:g[t],pts:pts.reverse()}}
function route(){if(routeLine)map.removeLayer(routeLine);const [a,da]=nearest(start),[b,db]=nearest(end);
 if(!a||!b){st('No legal roads nearby.');return}
 const r=astar(a,b);if(!r){st(`❌ No legal route in <b>${mode===35?'LSV':'golf cart'}</b> mode${allowUnk?'':' (try “allow unknown”)'}.`);return null}
 routeLine=L.polyline(r.pts.map(p=>[p[1],p[0]]),{color:'#2b6cff',weight:6,opacity:.85}).addTo(map);
 const mi=r.dist/1609.34,min=mi/(mode===35?25:18)*60;
 st(`✅ Legal route: <b>${mi.toFixed(1)} mi</b>, ~${Math.round(min)} min${da>150||db>150?' (start/end snapped to nearest legal road)':''}`);
 window.lastRoute={mi,min};return r}
function setPt(ll){if(!start||end){clearR();start=ll;mk.push(L.marker(ll).addTo(map).bindTooltip('Start'));st('Now tap the destination.')}
 else{end=ll;mk.push(L.marker(ll).addTo(map).bindTooltip('End'));route()}}
function clearR(){start=end=null;mk.forEach(m=>map.removeLayer(m));mk=[];if(routeLine)map.removeLayer(routeLine);routeLine=null;st('Tap map to set start.')}
map.on('click',e=>setPt(e.latlng));
$('clr').onclick=clearR;
function setMode(m){mode=m;$('mLSV').classList.toggle('on',m===35);$('mGC').classList.toggle('on',m===25);draw()}
$('mLSV').onclick=()=>setMode(35);$('mGC').onclick=()=>setMode(25);
$('unk').onchange=e=>{allowUnk=e.target.checked;buildGraph();if(start&&end)route()};
let me;$('loc').onclick=()=>navigator.geolocation.getCurrentPosition(p=>{const ll=L.latLng(p.coords.latitude,p.coords.longitude);
 if(me)map.removeLayer(me);me=L.circleMarker(ll,{radius:8,color:'#fff',fillColor:'#2b6cff',fillOpacity:1,weight:3}).addTo(map);map.setView(ll,16);
 clearR();start=ll;mk.push(L.marker(ll).addTo(map).bindTooltip('Start (you)'));st('Start = your location. Tap or search a destination.')},e=>st('Location unavailable: '+e.message),{enableHighAccuracy:true});
let tmr,lastQ=0;$('q').oninput=e=>{clearTimeout(tmr);const v=e.target.value.trim();if(v.length<4){$('sugg').style.display='none';return}
 tmr=setTimeout(async()=>{const wait=Math.max(0,1100-(Date.now()-lastQ));await new Promise(r=>setTimeout(r,wait));lastQ=Date.now();
  const b=D.meta.bbox;const r=await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=5&bounded=1&viewbox=${b[1]},${b[2]},${b[3]},${b[0]}&q=${encodeURIComponent(v)}`);
  const j=await r.json();const sg=$('sugg');sg.innerHTML='';sg.style.display=j.length?'block':'none';
  j.forEach(x=>{const d=document.createElement('div');d.textContent=x.display_name;d.onclick=()=>{sg.style.display='none';$('q').value=x.display_name.split(',')[0];
   const ll=L.latLng(+x.lat,+x.lon);map.setView(ll,15);if(start&&!end)setPt(ll);else if(start&&end){end=null;mk.pop()&&0;setPt(ll)}else{setPt(ll);st('Start set from search. Tap or search destination, or 📍 for your location.')}};sg.appendChild(d)})},700)};
window.testRoute=(a,b,m,u=false)=>{mode=m;allowUnk=u;buildGraph();clearR();start=L.latLng(a);end=L.latLng(b);const r=route();return r?{mi:+(r.dist/1609.34).toFixed(2),min:Math.round(window.lastRoute.min)}:null};
fetch('data/roads.json').then(r=>r.json()).then(j=>{D=j;const s=j.meta.stats;$('dmeta').textContent=`Data: OSM ${j.meta.generated}.`;draw();st('Tap map to set start, or 📍 Locate me.');window.ready=true});
