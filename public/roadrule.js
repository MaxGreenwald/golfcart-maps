// roadrule.js: the ONE road-rule module. The web app, CarPlay (via app.js), the Node tests and scripts/cart_impact.js all use it.
// Vehicle types: 'golf_cart' (plain golf cart / PTV / motorized cart) and 'lsv' (street-legal low-speed vehicle / NEV with VIN, plate, insurance).
// Thresholds live in data/rules.json (per state, per vehicle, each with a cite) and data/regions.json rule (region overrides;
// flat keys apply to both vehicles, rule.golf_cart / rule.lsv apply to one).
(function(root){
const VEHICLES=['golf_cart','lsv'];
// Default for a first visit. 'lsv' keeps today's map unchanged (LSV rule); 'golf_cart' is stricter but makes Florida mostly red until
// we have city/county designation lists (F.S. 316.212). PRODUCT DECISION for Max; see research/cart_vs_lsv.md.
const DEFAULT_VEH='lsv';
const VNAME={golf_cart:'golf carts',lsv:'LSVs'};
function ruleFor(rules,reg,veh){
  if(!VEHICLES.includes(veh))veh='golf_cart';
  const st=(rules&&rules[reg&&reg.state])||(rules&&rules.CA)||{},rr=(reg&&reg.rule)||{},flat={};
  for(const k in rr)if(k!=='golf_cart'&&k!=='lsv')flat[k]=rr[k];
  const base=st[veh]||{not_street_legal:true,unconfirmed:true,max_posted:0,cite:'No rule on file for this vehicle in '+(st.name||'this state')};
  const r={cross:true,...base,...flat,...(rr[veh]||{}),veh};
  if(r.not_street_legal)r.max_posted=0;
  return r}
const vname=r=>r.who||VNAME[r.veh]||'carts & LSVs';
const desig=(s,R)=>s[3]==='c'||s[3]==='d'||!!(R.assume&&R.assume.includes(s[1])&&s[2]!=null&&s[2]<=R.max_posted);
// cls: 0 posted ok, 1 assumed ok, 3 forbidden. Cart paths ('c') always ok; designated ('d') ok in designated-only mode.
// 'n'/'q' (scripts/islands.py): short same-road piece that takes the limit posted on both sides ('q' = sources disagree; app warns).
// s[9]===4: plain golf carts banned on this road by a local ordinance (source D.sources[s[10]]); LSVs unaffected; a posted sign never lifts it.
function cls(s,R,lenient){if(s[3]==='c')return 0;if(R.not_street_legal)return 3;if(s[9]===1&&/^(motorway|trunk|primary)/.test(s[1]))return 3;if(s[9]===4&&R.veh==='golf_cart')return 3;
  if(s[2]==null||(s[2]>R.max_posted&&!(lenient&&s[2]===99)))return 3;if(R.designated_only&&!desig(s,R))return 3;
  return s[3]==='t'||s[3]==='o'||s[3]==='v'||s[3]==='m'||s[3]==='d'||s[3]==='r'||s[3]==='k'||s[3]==='n'||s[3]==='q'?0:1}
const nextBand=m=>m%5?m+1:m+(m===25?1:5);
// why a segment is forbidden for this vehicle (popup text); '' when allowed
// src: the segment's source entry [url,label] (D.sources[s[8]]); a ban taken from a sheriff's LSV map names that map instead of the generic speed text.
function why(s,R,Rother,src){if(cls(s,R)!==3)return '';if(R.not_street_legal)return `Avoid: plain golf carts aren't street-legal here${R.unconfirmed?' (no rule on file)':''}${Rother&&cls(s,Rother)!==3?` (OK for ${vname(Rother)})`:''}`;
  if(s[9]===1&&/^(motorway|trunk|primary)/.test(s[1]))return 'Avoid: carts not allowed (posted)';
  if(s[9]===4&&R.veh==='golf_cart')return `Avoid: golf carts not allowed on this road (local ordinance)${Rother&&cls(s,Rother)!==3?` (OK for ${vname(Rother)})`:''}`;
  if(s[2]===99&&s[3]==='v'&&src&&/Sheriff LSV map/.test(src[1]||''))return `Avoid: LSVs not allowed here (${(src[1].match(/^[^:(]*Sheriff LSV map/)||['Sheriff LSV map'])[0].trim()})`;
  if(s[2]!=null&&s[2]<=R.max_posted&&R.designated_only)return `Avoid: ${vname(R)} only on cart paths and designated roads`;
  return `Avoid: ${nextBand(R.max_posted)}+ mph or major road${Rother&&cls(s,Rother)!==3?` (OK for ${vname(Rother)})`:''}`}
// text when no legal route exists
const noRoute=R=>R.not_street_legal?"Plain golf carts aren't street-legal here, so only cart paths count. Switch to 🚙 LSV if yours is street-legal.":R.designated_only?'Every way there leaves the cart paths/designated roads.':`Every way there uses a ${nextBand(R.max_posted)}+ mph road.`;
const api={DEFAULT_VEH,noRoute,VEHICLES,VNAME,ruleFor,cls,desig,why,vname,nextBand};
if(typeof module==='object'&&module.exports)module.exports=api;else root.GCMRule=api;
})(typeof window!=='undefined'?window:globalThis);
