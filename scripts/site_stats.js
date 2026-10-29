// Real scale numbers for the landing page, computed from public/data (same method as gcm/gtm/aeo/compute_stats.js):
// every tile segment, deduped, length by haversine; lsv_ok = miles the live roadrule.js lets an LSV drive.
const fs=require('fs'),path=require('path'),P=path.join(__dirname,'..','public','data')+'/';
const R=require(path.join(__dirname,'..','public','roadrule.js'));
const rules=JSON.parse(fs.readFileSync(P+'rules.json')),regs=JSON.parse(fs.readFileSync(P+'regions.json')).filter(r=>!r.hidden);
const hav=(a,b)=>{const r=Math.PI/180,dl=(b[1]-a[1])*r,dn=(b[0]-a[0])*r,x=Math.sin(dl/2)**2+Math.cos(a[1]*r)*Math.cos(b[1]*r)*Math.sin(dn/2)**2;return 7917.5*Math.asin(Math.sqrt(x))};
let mi=0,ok=0,n=0;
for(const reg of regs){const d=P+reg.id+'/tiles/';if(!fs.existsSync(d))continue;n++;const seen=new Set(),L=R.ruleFor(rules,reg,'lsv');
 for(const f of fs.readdirSync(d))for(const s of JSON.parse(fs.readFileSync(d+f))){const g=s[7],k=s[5]+'|'+s[6]+'|'+g[0]+'|'+g[g.length-1]+'|'+g.length;if(seen.has(k))continue;seen.add(k);
  let m=0;for(let i=1;i<g.length;i++)m+=hav(g[i-1],g[i]);mi+=m;if(R.cls(s,L)!==3)ok+=m;}}
process.stdout.write(JSON.stringify({road_mi:Math.round(mi),lsv_ok_mi:Math.round(ok),regions_with_tiles:n}));
