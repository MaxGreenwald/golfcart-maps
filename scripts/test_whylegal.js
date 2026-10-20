// Node test for public/whylegal.js: explanations match GCMRule.cls and cite the state rule + source.
const W=require('../public/whylegal.js'),G=require('../public/roadrule.js'),a=require('assert');
const rules=require('../public/data/rules.json');const R=G.ruleFor(rules,{state:'CA'},'lsv');
const src=[['https://example.gov/list.pdf','San Diego R-316675']];
const seg=(sp,f)=>[0,'residential',sp,f,0,1,2,[[0,0],[0,.001]],0];
const ctx=s=>({cls:G.cls(s,R),names:['Grand Ave'],sources:src,state:'California',reg:{}});
let s=seg(35,'v'),x=W.explain(s,R,ctx(s));a.ok(x.ok);a.equal(x.speed,'35 mph');a.equal(x.cite,'CVC 21260');a.match(x.rule,/35 mph or less/);a.equal(x.source.url,src[0][0]);a.match(x.source.detail,/R-316675/);
s=seg(45,'t');x=W.explain(s,R,ctx(s));a.ok(!x.ok);a.equal(x.verdict,'Not OK here');
s=seg(null,'i');x=W.explain(s,R,ctx(s));a.match(x.speed,/assumed 25/);a.match(x.source.label,/Assumed/);
s=seg(null,'c');x=W.explain(s,R,ctx(s));a.ok(x.ok);a.equal(x.speed,'Cart path');
const h=W.html(W.explain(seg(25,'m'),R,{cls:0,names:['<b>x'],sources:[['javascript:alert(1)','<script>']],state:'California',reg:{rule:{max_posted:25,cite:'Local ord',url:'https://x.gov'}}}));
a.ok(!/<script>/.test(h)&&!/javascript:/.test(h));a.match(h,/Local cap ≤25/);a.match(h,/Mapillary/);
a.equal(W.explain(seg(35,'v'),R,ctx(seg(35,'v'))).source.verified,null);a.ok(!/Last verified/.test(W.html(W.explain(seg(35,'v'),R,ctx(seg(35,'v'))))));
{const c2={...ctx(seg(35,'v')),sources:[['https://x.gov','L','2026-09-30']],dataDate:'2026-10-18'};const y=W.explain(seg(35,'v'),R,c2);a.equal(y.source.verified,'2026-09-30');a.match(W.html(y),/Last verified: 2026-09-30/);a.match(W.html(y),/Map data updated 2026-10-18/)}
{const c3={...ctx(seg(35,'v')),sources:[['https://x.gov','L','sometime']]};a.equal(W.explain(seg(35,'v'),R,c3).source.verified,null)}
// explain never changes legality: verdict always equals cls()!==3
for(const sp of [15,25,35,40,99,null])for(const f of 'tvmcdirknqi'){const s=seg(sp,f);a.equal(W.explain(s,R,ctx(s)).ok,G.cls(s,R)!==3)}
console.log('RESULT ALL PASS');
