const R=require('../public/range.js');const a=require('assert');
let c=R.check(10,25,100);a.equal(c.eff,25);a.equal(c.pct,40);a.equal(c.status,'ok');
c=R.check(20,25,100);a.equal(c.status,'ok');           // exactly 80%
c=R.check(18,25,80);a.equal(c.eff,20);a.equal(c.status,'tight'); // 90%
c=R.check(9.4,30,50);a.equal(c.pct,63);a.equal(c.status,'ok');
c=R.check(30,25,100);a.equal(c.status,'no');c=R.check(5,25,0);a.equal(c.status,'no');
a.equal(R.rangeFor('golf_cart',{}),25);a.equal(R.rangeFor('lsv',{}),30);a.equal(R.rangeFor('lsv',{range:{lsv:40}}),40);a.equal(R.rangeFor('lsv',{profile:'generic_golf_cart',range:{lsv:40}}),25);
console.log('RESULT ALL PASS');
