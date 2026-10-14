// Battery range check. Pure math in GCMRange.check(); range source is pluggable via GCMRange.profiles
// so a future make/model picker can just add entries ({id,label,mi}) and set settings.profile.
(function(g){
const DEFAULTS={golf_cart:25,lsv:30}, MARGIN=0.8, KEY='gcm-range';
const profiles={generic_golf_cart:{label:'Typical golf cart',mi:25},generic_lsv:{label:'Typical LSV',mi:30}};
function load(){try{return JSON.parse(localStorage.getItem(KEY))||{}}catch(_){return{}}}
function save(s){try{localStorage.setItem(KEY,JSON.stringify(s))}catch(_){}}
// settings: {range:{golf_cart:n,lsv:n}, battery:0-100, profile:id|null}
function rangeFor(mode,s){s=s||load();const p=s.profile&&profiles[s.profile];if(p)return p.mi;const r=s.range&&+s.range[mode];return r>0?r:DEFAULTS[mode]||25}
function check(roundMi,rangeMi,batteryPct){const b=Math.min(100,Math.max(0,+batteryPct||0));const eff=rangeMi*b/100;
 const pct=eff>0?roundMi/eff*100:Infinity;const status=pct<=MARGIN*100?'ok':pct<=100?'tight':'no';
 return {eff:+eff.toFixed(1),pct:Math.round(pct),status}}
g.GCMRange={DEFAULTS,MARGIN,profiles,load,save,rangeFor,check};
if(typeof module!=='undefined')module.exports=g.GCMRange;
})(typeof window!=='undefined'?window:globalThis);
