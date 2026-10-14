// Saved places storage (node scripts/test_places.js)
const store={};globalThis.localStorage={getItem:k=>k in store?store[k]:null,setItem:(k,v)=>{store[k]=String(v)},removeItem:k=>{delete store[k]}};
const S=require('../public/places.js'),a=require('assert');
a.deepEqual(S.load('sd'),{places:[],recents:[]});
const h=S.add('sd',{name:'Beach house',lat:32.8,lon:-117.27},'home');a.equal(S.get('sd','home').id,h.id);
const w=S.add('sd',{name:'Office',lat:32.71,lon:-117.16},'work');
const f=S.add('sd',{name:'Taco shop',sub:'restaurant',lat:32.79,lon:-117.25});a.equal(f.kind,'fav');
a.deepEqual(S.list('sd').map(p=>p.kind),['home','work','fav']);
// duplicate location returns the existing place, no new entry
a.equal(S.add('sd',{name:'Tacos again',lat:32.79001,lon:-117.25001}).id,f.id);a.equal(S.list('sd').length,3);
// only one Home: new Home demotes the old one
const h2=S.add('sd',{name:'New home',lat:32.85,lon:-117.27},'home');a.equal(S.get('sd','home').id,h2.id);a.equal(S.list('sd').find(p=>p.id===h.id).kind,'fav');
a.equal(S.rename('sd',f.id,'  Best tacos ').name,'Best tacos');a.equal(S.rename('sd',f.id,'   ').name,'Best tacos');
a.equal(S.setKind('sd',f.id,'work').kind,'work');a.equal(S.list('sd').find(p=>p.id===w.id).kind,'fav');
a.ok(S.remove('sd',w.id));a.ok(!S.remove('sd','nope'));a.equal(S.list('sd').length,3);
a.equal(S.find('sd',32.85,-117.27).id,h2.id);a.equal(S.find('sd',1,1),null);
// per region
a.equal(S.list('villages').length,0);S.add('villages',{name:'Spanish Springs',lat:28.91,lon:-81.97},'home');a.equal(S.list('villages').length,1);a.equal(S.get('sd','home').id,h2.id);
// recents: newest first, deduped, capped at 10
for(let i=0;i<14;i++)S.addRecent('sd',{name:'Place '+i,lat:32+i/100,lon:-117});
let r=S.recents('sd');a.equal(r.length,10);a.equal(r[0].name,'Place 13');
S.addRecent('sd',{name:'Place 7',lat:32.07,lon:-117});r=S.recents('sd');a.equal(r[0].name,'Place 7');a.equal(r.length,10);a.equal(r.filter(x=>x.name==='Place 7').length,1);
S.clearRecents('sd');a.equal(S.recents('sd').length,0);a.equal(S.list('sd').length,3);
// corrupt storage is tolerated
store['gcm-places:bad']='{oops';a.deepEqual(S.load('bad'),{places:[],recents:[]});
console.log('RESULT ALL PASS');
