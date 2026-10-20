// Node test for public/routeopts.js: profile costs never drop below length (A* stays admissible), legality is never
// changed by a profile, the % verified score, duplicate detection and the scenic POI index.
const O=require('../public/routeopts.js'),G=require('../public/roadrule.js'),a=require('assert');
const R=G.ruleFor(require('../public/data/rules.json'),{state:'CA'},'lsv');
const seg=(hw,sp,f,pts)=>[0,hw,sp,f,0,1,2,pts||[[-117.25,32.8],[-117.25,32.801]],0];
const segs=[];for(const hw of ['residential','tertiary','secondary','path','living_street','service'])for(const sp of [null,15,25,35,99])for(const f of 'tvmcdinqk')segs.push(seg(hw,sp,f));
for(const id of O.ORDER){const P=O.PROFILES[id];a.ok(P.label&&P.icon);for(const s of segs)for(const x of [{},{scenic:true},{caution:true}]){const c=P.cost(s,100,G.cls(s,R),x);a.ok(c>=100-1e-9,`${id} cost ${c} < length`)}}
// fastest prefers a 35 mph collector over an equal-length residential street; shortest is pure length
a.ok(O.PROFILES.fastest.cost(seg('tertiary',35,'t'),100)<O.PROFILES.fastest.cost(seg('residential',25,'t'),100));
a.equal(O.PROFILES.shortest.cost(seg('tertiary',35,'t'),123),123);
// most verified prefers posted over assumed; scenic prefers flagged scenic roads
a.ok(O.PROFILES.legal.cost(seg('residential',25,'v'),100,0)<O.PROFILES.legal.cost(seg('residential',null,'i'),100,1));
a.ok(O.PROFILES.scenic.cost(seg('residential',25,'t'),100,0,{scenic:true})<O.PROFILES.scenic.cost(seg('tertiary',35,'t'),100,0,{}));
// verified never counts a forbidden segment
a.equal(O.verified(seg('secondary',45,'t'),3),false);a.equal(O.verified(seg('residential',null,'i'),1),false);a.equal(O.verified(seg('residential',25,'m'),0),true);
// score: 300 m verified + 100 m assumed = 75%
const L=(s,len)=>(s._len=len,{s});a.equal(O.score([L(seg('residential',25,'v'),300),L(seg('residential',null,'i'),100)],s=>G.cls(s,R)),75);a.equal(O.score([],()=>0),0);
// same(): 95% overlap is a duplicate, 50% is not
a.ok(O.same([[1,0,95],[2,0,5]],[[1,0,95],[3,0,5]]));a.ok(!O.same([[1,0,50],[2,0,50]],[[1,0,50],[3,0,50]]));
// scenic index: residential next to a park is scenic; an arterial next to it or a street 1 km away is not
const sc=O.scenicIndex([['Kate Sessions Park','park',-117.25,32.8005,''],['Taco','restaurant',-117.2,32.9,'']]);
a.ok(sc(seg('residential',25,'t')));a.ok(!sc(seg('secondary',35,'t')));a.ok(!sc(seg('residential',25,'t',[[-117.24,32.81],[-117.24,32.811]])));
a.equal(O.mph(seg('residential',15,'t')),15);a.equal(O.mph(seg('path',null,'c')),12);
console.log('RESULT ALL PASS');
