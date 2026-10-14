// Battery range check. Pure math in GCMRange.check(); range source is pluggable via GCMRange.profiles
// so a future make/model picker can just add entries ({id,label,mi}) and set settings.profile.
(function(g){
const DEFAULT=30, MARGIN=0.8, KEY='gcm-range';
const profiles={generic:{label:'Typical cart / LSV',mi:30}};
// migrate old per-mode {range:{golf_cart,lsv}}: keep a value the user actually changed (LSV first), else default
function migrate(s){if(s&&s.range&&typeof s.range==='object'){const g=+s.range.golf_cart,l=+s.range.lsv;s.range=l>0&&l!==30?l:g>0&&g!==25?g:DEFAULT;if(s.profile&&!profiles[s.profile])s.profile=null}return s}
function load(){try{const raw=localStorage.getItem(KEY),s=migrate(JSON.parse(raw)||{});if(raw&&JSON.stringify(s)!==raw)save(s);return s}catch(_){return{}}}
function save(s){try{localStorage.setItem(KEY,JSON.stringify(s))}catch(_){}}
// settings: {range:n (mi), battery:0-100, profile:id|null}
function rangeFor(s){s=s||load();const p=s.profile&&profiles[s.profile];if(p)return p.mi;const r=+s.range;return r>0?r:DEFAULT}
function check(roundMi,rangeMi,batteryPct){const b=Math.min(100,Math.max(0,+batteryPct||0));const eff=rangeMi*b/100;
 const pct=eff>0?roundMi/eff*100:Infinity;const status=pct<=MARGIN*100?'ok':pct<=100?'tight':'no';
 return {eff:+eff.toFixed(1),pct:Math.round(pct),status}}
g.GCMRange={DEFAULT,migrate,MARGIN,profiles,load,save,rangeFor,check};
if(typeof module!=='undefined')module.exports=g.GCMRange;
})(typeof window!=='undefined'?window:globalThis);
