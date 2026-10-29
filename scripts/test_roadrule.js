// Unit tests for public/roadrule.js (the single road-rule module) + rules.json/regions.json vehicle profiles.
// run: node scripts/test_roadrule.js
const R=require('../public/roadrule.js'),a=require('assert'),fs=require('fs'),path=require('path');
const PUB=path.join(__dirname,'..','public'),rules=JSON.parse(fs.readFileSync(PUB+'/data/rules.json')),regs=JSON.parse(fs.readFileSync(PUB+'/data/regions.json'));
const reg=id=>regs.find(r=>r.id===id),seg=(mph,src='t',hw='residential',flag)=>{const s=[0,hw,mph,src,0,1,2,[[0,0],[0,0.001]],0];if(flag!=null)s[9]=flag;return s};
let n=0;const t=(name,f)=>{f();n++;console.log('PASS',name)};
const CA=reg('sd'),cart=R.ruleFor(rules,CA,'golf_cart'),lsv=R.ruleFor(rules,CA,'lsv');
t('CA golf cart cap is 25 (CVC 21716)',()=>{a.equal(cart.max_posted,25);a.match(cart.cite,/21716/)});
t('CA: 25 mph road OK for golf carts',()=>{a.notEqual(R.cls(seg(25),cart),3);a.notEqual(R.cls(seg(20),cart),3)});
t('CA: 30 and 35 mph roads are Avoid for golf carts',()=>{a.equal(R.cls(seg(30),cart),3);a.equal(R.cls(seg(35),cart),3);a.equal(R.cls(seg(30,'v'),cart),3);a.equal(R.cls(seg(35,'m','secondary'),cart),3)});
t('CA: 30 and 35 mph roads OK for LSVs (CVC 21260)',()=>{a.equal(R.cls(seg(30),lsv),0);a.equal(R.cls(seg(35),lsv),0)});
t('CA: 40 mph Avoid for both',()=>{a.equal(R.cls(seg(40),cart),3);a.equal(R.cls(seg(40),lsv),3)});
t('unknown speed (99) Avoid unless lenient',()=>{a.equal(R.cls(seg(99),lsv),3);a.notEqual(R.cls(seg(99),lsv,true),3);a.equal(R.cls(seg(null),cart),3)});
t("same-road codes 'n'/'q' (scripts/islands.py) count as posted; golf carts still follow the limit",()=>{for(const c of ['n','q']){a.equal(R.cls(seg(35,c,'secondary'),lsv),0);a.equal(R.cls(seg(35,c,'secondary'),cart),3);a.equal(R.cls(seg(25,c),cart),0)}});
t('cart paths OK for every vehicle in every region',()=>{for(const r of regs)for(const v of R.VEHICLES)a.equal(R.cls(seg(null,'c','path'),R.ruleFor(rules,r,v)),0,r.id+' '+v)});
t('every CA region: golf cart cap <= 25',()=>{for(const r of regs.filter(r=>r.state==='CA')){const g=R.ruleFor(rules,r,'golf_cart');a.ok(g.max_posted<=25,r.id);a.equal(R.cls(seg(30),g),3,r.id)}});
t('every state has a golf_cart and an lsv profile with a cite',()=>{for(const st of new Set(regs.map(r=>r.state))){for(const v of R.VEHICLES){a.ok(rules[st][v],st+' '+v);a.ok(rules[st][v].cite,st+' '+v+' cite')}}});
t('HI/ME: plain golf carts not street-legal, LSVs <=35',()=>{for(const id of ['wailea','kailua','waikoloa','oob']){const g=R.ruleFor(rules,reg(id),'golf_cart'),l=R.ruleFor(rules,reg(id),'lsv');a.ok(g.not_street_legal);a.equal(R.cls(seg(25),g),3);a.equal(R.cls(seg(35),l),0);a.match(R.why(seg(25),g,l),/aren't street-legal.*OK for/)}});
t('Sheriff-map bans name the map, not the speed',()=>{const l=R.ruleFor(rules,reg('30a'),'lsv');const s=[0,'secondary',99,'v',0,0,1,[],0];
  a.equal(R.why(s,l,null,['https://waltonso.org/lsv/','Walton County Sheriff LSV map (red = prohibited): CR 283 (US 98 to the bay and south to 30A)']),'Avoid: LSVs not allowed here (Walton County Sheriff LSV map)');
  a.equal(R.why(s,l,null,['https://waltonso.org/lsv/','Walton County Sheriff: LSVs may not drive on US 98']),'Avoid: 40+ mph or major road');a.equal(R.why(s,l),'Avoid: 40+ mph or major road')});
t('FL golf carts: designated roads only',()=>{const g=R.ruleFor(rules,reg('villages'),'golf_cart');a.ok(g.designated_only);a.equal(R.cls(seg(25,'t'),g),3);a.equal(R.cls(seg(25,'d'),g),0);a.equal(R.cls(seg(35,'d'),g),0);a.equal(R.cls(seg(40,'d'),g),3);a.match(R.why(seg(25,'t'),g),/designated/);
  a.equal(R.cls(seg(35,'t'),R.ruleFor(rules,reg('villages'),'lsv')),0)});
t('region flat rule applies to both vehicles (Gulf Shores <=25)',()=>{for(const v of R.VEHICLES){const x=R.ruleFor(rules,reg('gulfshores'),v);a.equal(x.max_posted,25);a.equal(R.cls(seg(30),x),3)}});
t('region per-vehicle rule applies to one vehicle (Coachella golf cart note)',()=>{a.match(R.ruleFor(rules,reg('coachella'),'golf_cart').note,/golf cart plans/);a.equal(R.ruleFor(rules,reg('coachella'),'lsv').note,undefined)});
t('posted no-carts major road Avoid for both',()=>{a.equal(R.cls(seg(25,'t','primary',1),lsv),3);a.equal(R.cls(seg(25,'t','primary',1),cart),3)});
t('vehicle names and popup reasons',()=>{a.equal(R.vname(cart),'golf carts');a.equal(R.vname(lsv),'LSVs');a.equal(R.vname(R.ruleFor(rules,reg('wailea'),'lsv')),'street-legal electric LSVs');
  a.equal(R.why(seg(30),cart,lsv),'Avoid: 26+ mph or major road (OK for LSVs)');a.equal(R.why(seg(40),lsv,cart),'Avoid: 40+ mph or major road');a.equal(R.why(seg(25),cart),'');
  a.match(R.noRoute(cart),/26\+ mph/);a.match(R.noRoute(R.ruleFor(rules,reg('oob'),'golf_cart')),/street-legal/)});
t('unknown vehicle falls back to golf cart; default is a known vehicle',()=>{a.equal(R.ruleFor(rules,CA,'bogus').veh,'golf_cart');a.ok(R.VEHICLES.includes(R.DEFAULT_VEH))});
t('LSV rule unchanged from master (<=35 everywhere except region caps, NJ 25, and CT 25)',()=>{for(const r of regs){const l=R.ruleFor(rules,r,'lsv');a.equal(l.max_posted,(r.rule&&r.rule.max_posted)||(r.state==='NJ'||r.state==='CT'?25:35),r.id);a.ok(!l.designated_only,r.id)}});  // NJ: N.J.S.A. 39:4-31.1. CT: Conn. Gen. Stat. Sec. 14-289m (P.A. 24-20), LSVs on roads posted 25 mph or less.
t('LSV mode classifies every real segment exactly like master app.js did',()=>{
  const old=(s,RULE,LEN)=>{const desig=s=>s[3]==='c'||s[3]==='d'||(RULE.assume&&RULE.assume.includes(s[1])&&s[2]!=null&&s[2]<=RULE.max_posted);if(s[3]==='c')return 0;if(s[9]===1&&/^(motorway|trunk|primary)/.test(s[1]))return 3;if(s[2]==null||(s[2]>RULE.max_posted&&!(LEN&&s[2]===99)))return 3;if(RULE.designated_only&&!desig(s))return 3;return s[3]==='t'||s[3]==='v'||s[3]==='m'||s[3]==='d'||s[3]==='r'||s[3]==='k'||s[3]==='n'||s[3]==='q'?0:1};  // + same-road codes n/q (Oct 18 2026)
  let k=0;for(const r of regs){const dir=path.join(PUB,'data',r.id,'tiles');if(!fs.existsSync(dir))continue;const st=rules[r.state]||rules.CA,M={...st.lsv,...(r.rule||{})},N=R.ruleFor(rules,r,'lsv');
    for(const f of fs.readdirSync(dir))for(const s of JSON.parse(fs.readFileSync(path.join(dir,f)))){const s0=s[3]==='o'?[...s.slice(0,3),'t',...s.slice(4)]:s;  // trusted OSM 'o' must classify exactly like the OSM tag 't' it relabels
    for(const L of [false,true])a.equal(R.cls(s,N,L),old(s0,M,L),r.id+' '+JSON.stringify(s.slice(0,4)));k++}}
  a.ok(k>100000,'segments checked '+k)});
t('flag 4 (local golf-cart-only ban): Avoid for golf carts, LSVs unaffected, a posted sign never lifts it',()=>{for(const id of ['annamaria','rockport','chs','staug']){const g=R.ruleFor(rules,reg(id),'golf_cart'),l=R.ruleFor(rules,reg(id),'lsv');
  for(const c of ['t','v','m','o','d']){const s=[0,'residential',25,c,0,0,1,[],-1,4,0];a.equal(R.cls(s,g),3,id+' '+c);a.equal(R.cls(s,l),0,id+' '+c);a.match(R.why(s,g,l),/golf carts not allowed on this road \(local ordinance\).*OK for/)}}});
t('South Padre: local cap 35 cites Sec. 18-30',()=>{for(const v of R.VEHICLES){const x=R.ruleFor(rules,reg('southpadre'),v);a.equal(x.max_posted,35);a.match(x.cite,/18-30/);a.equal(R.cls(seg(40),x),3)}});
console.log(`RESULT ALL PASS (${n})`);
