// Node test for public/places.js (localStorage shim): Home unique, favorites, recents cap, share link round trip.
const store={};globalThis.localStorage={getItem:k=>k in store?store[k]:null,setItem:(k,v)=>{store[k]=String(v)}};
const P=require('../public/places.js'),a=require('assert');
const h=P.add('sd',{name:'Beach house',lat:32.8,lon:-117.25},'home');a.equal(P.get('sd','home').name,'Beach house');
const h2=P.add('sd',{name:'New home',lat:32.81,lon:-117.26},'home');a.equal(P.get('sd','home').id,h2.id);a.equal(P.list('sd').find(x=>x.id===h.id).kind,'fav');
a.equal(P.list('sd')[0].kind,'home');                                  // Home sorts first
const f=P.add('sd',{name:'Taco shop',lat:32.79,lon:-117.24});a.equal(f.kind,'fav');
a.equal(P.add('sd',{name:'dup',lat:32.79001,lon:-117.24001}).id,f.id); // same spot is not saved twice
P.rename('sd',f.id,'  Best tacos ');a.equal(P.find('sd',32.79,-117.24).name,'Best tacos');
a.ok(P.remove('sd',f.id));a.equal(P.find('sd',32.79,-117.24),null);
a.equal(P.list('villages').length,0);                                  // per region
for(let i=0;i<14;i++)P.addRecent('sd',{name:'R'+i,lat:32+i/100,lon:-117});a.equal(P.recents('sd').length,P.MAXR);a.equal(P.recents('sd')[0].name,'R13');
// share link round trip; junk input is rejected
const u=P.link('sandiego',{name:'Tourmaline & Co',lat:32.80512345,lon:-117.2622});a.ok(u.startsWith('https://golfcartmap.com/sandiego?'));
const back=P.parsePin(new URL(u).search);a.deepEqual(back,{name:'Tourmaline & Co',lat:32.80512,lon:-117.2622});
a.equal(P.parsePin('?lat=32.8&lon=-117.2'),null);a.equal(P.parsePin('?lat=999&lon=1&pin=x'),null);a.equal(P.parsePin('?lat=abc&lon=1&pin=x'),null);
a.equal(P.parsePin('?lat=32&lon=-117&pin='+'x'.repeat(200)).name.length,60);
// nothing but places is written (no accounts, no ids beyond local)
a.deepEqual(Object.keys(store),['gcm-places:sd']);
console.log('RESULT ALL PASS');
