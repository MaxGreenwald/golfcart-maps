// Node test for the battery math in public/range.js: arrival %, round trip, D5 4+2 preset, full-cart estimate.
const R=require('../public/range.js'),a=require('assert');
a.equal(R.profiles.d5_42.mi,30);a.match(R.profiles.d5_42.src,/Beach Mode/);
a.equal(R.rangeFor({profile:'d5_42',range:50}),30);                        // preset overrides custom range
a.equal(R.effRange({range:30}),30);a.equal(R.effRange({range:30,full:true}),26.4);  // -12% estimate only when turned on
a.equal(R.FULL_DERATE,0.12);
let x=R.arrival(3,6,30,100);a.deepEqual(x,{one:90,rt:80,oneShort:false,rtShort:false});
x=R.arrival(3,6,30,50);a.equal(x.one,40);a.equal(x.rt,30);
x=R.arrival(10,20,30,50);a.equal(x.one,17);a.equal(x.rt,0);a.ok(x.rtShort);a.ok(!x.oneShort);
x=R.arrival(1,2,30,0);a.ok(x.oneShort&&x.rtShort);
x=R.arrival(1,2,0,100);a.ok(x.oneShort);                                  // no range -> never claims charge left
a.equal(R.arrival(3,6,30,150).one,90);                                     // battery clamped to 100
// multi-stop: whole trip miles feed both numbers the same way
const leg=[1.2,0.8,2.0],trip=leg.reduce((s,v)=>s+v,0),back=2.5;x=R.arrival(trip,trip+back,30,100);a.equal(x.one,87);a.equal(x.rt,78);
// existing check() unchanged
a.equal(R.check(20,25,100).status,'ok');a.equal(R.check(30,25,100).status,'no');
console.log('RESULT ALL PASS');
