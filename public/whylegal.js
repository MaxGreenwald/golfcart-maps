// whylegal.js: "why is this road legal?" for one segment. Pure (no DOM), shared by the road popup,
// the live in-route strip and the Node test (scripts/test_whylegal.js). Reuses the existing data:
// segment speed/source flag (s[2], s[3], s[8]), the state rule from data/rules.json (cite) and any
// region local cap (REG.rule). Never decides legality itself: it explains GCMRule.cls().
(function(root){
const SRC={t:'OpenStreetMap speed tag',v:'City/county speed list',m:'Posted sign photo (Mapillary)',c:'Cart path',d:'Designated cart road',
 r:'Roundabout (uses its connecting roads)',k:'Turn lane (uses its connecting roads)',n:'Same road posted on both sides',q:'Sources disagree'};
// s: segment, R: rule (GCMRule.ruleFor), ctx: {cls, names, sources, state, reg}
function explain(s,R,ctx){ctx=ctx||{};const c=ctx.cls,sp=s[2],src=ctx.sources&&ctx.sources[s[8]];
 const road=(ctx.names&&ctx.names[s[0]])||'Unnamed road';
 const speed=s[3]==='c'?'Cart path':sp==null||sp===99?'No posted limit found (assumed 25 mph)':sp+' mph';
 const ok=c!==3;
 let rule;
 if(s[3]==='c')rule='Cart paths are always OK for carts and LSVs.';
 else if(R.not_street_legal)rule=`In ${ctx.state||'this state'}, plain golf carts aren't street-legal: cart paths only.`;
 else if(R.designated_only)rule=`In ${ctx.state||'this state'}, ${R.who||'carts'} may use cart paths and designated roads posted ≤${R.max_posted} mph.`;
 else rule=`In ${ctx.state||'this state'}, roads posted ${R.max_posted} mph or less are OK; faster roads are not.`;
 const reg=ctx.reg&&ctx.reg.rule&&ctx.reg.rule.cite?{text:`Local cap ≤${ctx.reg.rule.max_posted} mph: ${ctx.reg.rule.cite}`,url:ctx.reg.rule.url||null}:null;
 const source={label:SRC[s[3]]||'Assumed from road type (no posted limit found)',
   detail:src?src[1]:null,url:src&&/^https?:/.test(src[0]||'')?src[0]:null,
   // last-verified date only when the source row carries one ([url,label,'YYYY-MM-DD']); never inferred
   verified:src&&/^\d{4}-\d{2}-\d{2}$/.test(src[2]||'')?src[2]:null};
 return {dataDate:ctx.dataDate||null,road,speed,ok,verdict:ok?'OK here':'Not OK here',rule,cite:R.cite||null,local:reg,source}}
const esc=t=>String(t??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function html(x){const a=(u,t)=>u?`<a href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}</a>`:esc(t);
 return `<div class="why"><div class="whyh">${x.ok?'✅':'⛔'} Why it's ${x.ok?'OK':'not OK'}: <b>${esc(x.speed)}</b></div>`+
  `<div>${esc(x.rule)}${x.cite?` <span class="cite">(${esc(x.cite)})</span>`:''}</div>`+
  (x.local?`<div>${a(x.local.url,x.local.text)}</div>`:'')+
  `<div class="cite">Speed source: ${a(x.source.url,x.source.label+(x.source.detail?': '+x.source.detail:''))}</div>`+
  (x.source.verified?`<div class="cite">Last verified: ${esc(x.source.verified)}</div>`:'')+
  (x.dataDate?`<div class="cite">Map data updated ${esc(x.dataDate)}</div>`:'')+`</div>`}
const api={explain,html,SRC};
if(typeof module==='object'&&module.exports)module.exports=api;else root.GCMWhy=api;
})(typeof window!=='undefined'?window:globalThis);
