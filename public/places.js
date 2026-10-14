// Saved places (Home, Work, favorites) + recent searches, stored in localStorage per region.
(function(g){
const K=r=>'gcm-places:'+(r||'sd'),MAXR=10;
const ls=()=>{try{return g.localStorage}catch(_){return null}};
const rid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,6);
function load(r){try{const j=JSON.parse(ls().getItem(K(r)));if(j&&Array.isArray(j.places))return {places:j.places,recents:Array.isArray(j.recents)?j.recents:[]}}catch(_){}return {places:[],recents:[]}}
function save(r,d){try{ls().setItem(K(r),JSON.stringify(d))}catch(_){}return d}
const near=(a,b)=>Math.abs(a.lat-b.lat)<0.0002&&Math.abs(a.lon-b.lon)<0.0002;
// kind: 'home' | 'work' | 'fav'. Home/Work are unique: setting a new one demotes the old one to a favorite.
function add(r,p,kind){const d=load(r);kind=kind||'fav';const x={id:rid(),name:String(p.name||'Saved place').slice(0,80),sub:p.sub?String(p.sub).slice(0,120):'',lat:+(+p.lat).toFixed(6),lon:+(+p.lon).toFixed(6),kind};
 const dup=d.places.find(q=>near(q,x));if(dup){if(kind!=='fav')setKind(r,dup.id,kind);return load(r).places.find(q=>q.id===dup.id)}
 if(kind!=='fav')d.places.forEach(q=>{if(q.kind===kind)q.kind='fav'});d.places.push(x);save(r,d);return x}
function setKind(r,id,kind){const d=load(r);const x=d.places.find(q=>q.id===id);if(!x)return null;if(kind!=='fav')d.places.forEach(q=>{if(q.kind===kind)q.kind='fav'});x.kind=kind;save(r,d);return x}
function rename(r,id,name){const d=load(r);const x=d.places.find(q=>q.id===id);if(!x)return null;x.name=String(name||'').trim().slice(0,80)||x.name;save(r,d);return x}
function remove(r,id){const d=load(r);const n=d.places.length;d.places=d.places.filter(q=>q.id!==id);save(r,d);return d.places.length<n}
function find(r,lat,lon){return load(r).places.find(q=>near(q,{lat,lon}))||null}
function list(r){const ps=load(r).places,o={home:2,work:1,fav:0};return ps.slice().sort((a,b)=>o[b.kind]-o[a.kind])}
function get(r,kind){return load(r).places.find(q=>q.kind===kind)||null}
function addRecent(r,p){const d=load(r);const x={name:String(p.name||'').slice(0,80),sub:p.sub?String(p.sub).slice(0,120):'',lat:+(+p.lat).toFixed(6),lon:+(+p.lon).toFixed(6)};if(!x.name)return d.recents;
 d.recents=[x,...d.recents.filter(q=>!(near(q,x)||q.name===x.name))].slice(0,MAXR);save(r,d);return d.recents}
function recents(r){return load(r).recents}
function clearRecents(r){const d=load(r);d.recents=[];save(r,d)}
g.GCMPlaces={load,add,setKind,rename,remove,find,list,get,addRecent,recents,clearRecents,MAXR};
if(typeof module!=='undefined')module.exports=g.GCMPlaces;
})(typeof window!=='undefined'?window:globalThis);
