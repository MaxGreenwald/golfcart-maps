// Per-region impact of the golf cart vs LSV split, using the same rule module the app uses (public/roadrule.js).
// "Affected" = road the map labels OK (green, "OK for carts & LSVs" on master) under the LSV rule but Avoid under the golf cart rule.
// usage: node scripts/cart_impact.js [--json out.json]
const fs=require('fs'),path=require('path'),R=require('../public/roadrule.js');
const PUB=path.join(__dirname,'..','public'),rules=JSON.parse(fs.readFileSync(PUB+'/data/rules.json')),regs=JSON.parse(fs.readFileSync(PUB+'/data/regions.json'));
const hav=(a,b)=>{const r=Math.PI/180,dl=(b[1]-a[1])*r,dn=(b[0]-a[0])*r,x=Math.sin(dl/2)**2+Math.cos(a[1]*r)*Math.cos(b[1]*r)*Math.sin(dn/2)**2;return 12742000*Math.asin(Math.sqrt(x))};
const len=p=>{let d=0;for(let i=1;i<p.length;i++)d+=hav(p[i-1],p[i]);return d};
const unk=(reg,s,R0)=>reg.id!=='sd'&&reg.id!=='villages'&&s[3]==='i'&&/^(secondary|tertiary|unclassified)/.test(s[1])&&R.cls(s,R0)!==3;
const out=[];
for(const reg of regs){const dir=path.join(PUB,'data',reg.id,'tiles');if(!fs.existsSync(dir))continue;
  const L=R.ruleFor(rules,reg,'lsv'),G=R.ruleFor(rules,reg,'golf_cart'),seen=new Set();
  const o={id:reg.id,state:reg.state,cart_max:G.not_street_legal?0:G.max_posted,lsv_max:L.max_posted,designated_only:!!G.designated_only,not_street_legal:!!G.not_street_legal,
    road_km:0,lsv_ok_km:0,cart_ok_km:0,affected_km:0,by_speed:{},by_reason:{speed:0,designation:0,not_street_legal:0},affected_unknown_speed_km:0,top:{}};
  let names=[];try{names=JSON.parse(fs.readFileSync(path.join(PUB,'data',reg.id,'index.json'))).names||[]}catch(_){}
  for(const f of fs.readdirSync(dir)){for(const s of JSON.parse(fs.readFileSync(path.join(dir,f)))){
    if(s[3]==='c')continue;const k=s[5]+'_'+s[6]+'_'+s[7][0];if(seen.has(k))continue;seen.add(k);
    const m=len(s[7])/1000;o.road_km+=m;const cl=R.cls(s,L),cg=R.cls(s,G);if(cl!==3)o.lsv_ok_km+=m;if(cg!==3)o.cart_ok_km+=m;
    if(cl!==3&&cg===3){if(unk(reg,s,L)){o.affected_unknown_speed_km+=m;continue}
      o.affected_km+=m;const why=G.not_street_legal?'not_street_legal':(s[2]!=null&&s[2]<=G.max_posted&&G.designated_only)?'designation':'speed';o.by_reason[why]+=m;
      const b=String(s[2]);o.by_speed[b]=(o.by_speed[b]||0)+m;if(why==='speed'){const n=names[s[0]]||'(unnamed)';o.top[n+' '+s[2]]=(o.top[n+' '+s[2]]||0)+m}}}}
  const r1=x=>Math.round(x*10)/10;for(const k of ['road_km','lsv_ok_km','cart_ok_km','affected_km','affected_unknown_speed_km'])o[k]=r1(o[k]);
  for(const k in o.by_reason)o.by_reason[k]=r1(o.by_reason[k]);for(const k in o.by_speed)o.by_speed[k]=r1(o.by_speed[k]);
  o.top=Object.entries(o.top).sort((a,b)=>b[1]-a[1]).slice(0,4).map(([n,v])=>n+' mph '+r1(v)+'km');o.speed_30_35_km=r1((o.by_speed['30']||0)+(o.by_speed['35']||0)+(o.by_speed['26']||0)+(o.by_speed['27']||0));
  out.push(o)}
const i=process.argv.indexOf('--json');if(i>0)fs.writeFileSync(process.argv[i+1],JSON.stringify(out,null,1));
console.log('region st cartMax road_km lsvOK_km cartOK_km AFFECTED_km speed desig notLegal unk_km 30-35mph');
for(const o of out)console.log([o.id,o.state,o.not_street_legal?'none':o.cart_max+(o.designated_only?'D':''),o.road_km,o.lsv_ok_km,o.cart_ok_km,o.affected_km,o.by_reason.speed,o.by_reason.designation,o.by_reason.not_street_legal,o.affected_unknown_speed_km,o.speed_30_35_km].join(' '));
const T=k=>Math.round(out.reduce((a,o)=>a+(k(o)||0),0));console.log('TOTAL affected_km',T(o=>o.affected_km),'speed',T(o=>o.by_reason.speed),'desig',T(o=>o.by_reason.designation),'notlegal',T(o=>o.by_reason.not_street_legal));
