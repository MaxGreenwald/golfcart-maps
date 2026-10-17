const R=require('../public/range.js');const a=require('assert');
let c=R.check(10,25,100);a.equal(c.eff,25);a.equal(c.pct,40);a.equal(c.status,'ok');
c=R.check(20,25,100);a.equal(c.status,'ok');           // exactly 80%
c=R.check(18,25,80);a.equal(c.eff,20);a.equal(c.status,'tight'); // 90%
c=R.check(9.4,30,50);a.equal(c.pct,63);a.equal(c.status,'ok');
c=R.check(30,25,100);a.equal(c.status,'no');c=R.check(5,25,0);a.equal(c.status,'no');
a.equal(R.rangeFor({}),30);a.equal(R.rangeFor({range:40}),40);a.equal(R.rangeFor({profile:'generic',range:40}),30);
a.equal(R.migrate({range:{golf_cart:25,lsv:30}}).range,30);a.equal(R.migrate({range:{golf_cart:18,lsv:30}}).range,18);a.equal(R.migrate({range:{golf_cart:25,lsv:42}}).range,42);a.equal(R.migrate({range:{golf_cart:25,lsv:30},profile:'generic_lsv'}).profile,null);
console.log('RESULT ALL PASS');
