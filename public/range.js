// Battery range check. Pure math in GCMRange.check(); range source is pluggable via GCMRange.profiles
// so a future make/model picker can just add entries ({id,label,mi}) and set settings.profile.
(function(g){
const DEFAULT=30, MARGIN=0.8, KEY='gcm-range';
const profiles={generic:{label:'Typical cart / LSV',mi:30},
 // Evolution D5 4+2: ~30 mi per Beach Mode Rentals (Brian, Oct 2026; whole fleet is D5 4+2), "less with six people aboard"
 d5_42:{label:'Evolution D5 4+2',mi:30,src:'Beach Mode Rentals (fleet owner estimate)'}};
// A full cart (5-6 riders) uses more energy. No measured number yet, so this is a labeled ESTIMATE (-12%).
const FULL_DERATE=0.12;
// migrate old per-mode {range:{golf_cart,lsv}}: keep a value the user actually changed (LSV first), else default
function migrate(s){if(s&&s.range&&typeof s.range==='object'){const g=+s.range.golf_cart,l=+s.range.lsv;s.range=l>0&&l!==30?l:g>0&&g!==25?g:DEFAULT;if(s.profile&&!profiles[s.profile])s.profile=null}return s}
function load(){try{const raw=localStorage.getItem(KEY),s=migrate(JSON.parse(raw)||{});if(raw&&JSON.stringify(s)!==raw)save(s);return s}catch(_){return{}}}
function save(s){try{localStorage.setItem(KEY,JSON.stringify(s))}catch(_){}}
// settings: {range:n (mi), battery:0-100, profile:id|null}
function rangeFor(s){s=s||load();const p=s.profile&&profiles[s.profile];if(p)return p.mi;const r=+s.range;return r>0?r:DEFAULT}
// effective range after the full-cart estimate (only when the user turned it on)
function effRange(s){s=s||load();const r=rangeFor(s);return s.full?+(r*(1-FULL_DERATE)).toFixed(1):r}
// battery % left on arrival: one way (oneMi) and back home (rtMi = whole trip incl. stops + return)
function arrival(oneMi,rtMi,rangeMi,batteryPct){const b=Math.min(100,Math.max(0,+batteryPct||0)),use=mi=>rangeMi>0?mi/rangeMi*100:Infinity;
 const o=b-use(oneMi),r=b-use(rtMi);return {one:Math.max(0,Math.round(o)),rt:Math.max(0,Math.round(r)),oneShort:o<0,rtShort:r<0}}
function check(roundMi,rangeMi,batteryPct){const b=Math.min(100,Math.max(0,+batteryPct||0));const eff=rangeMi*b/100;
 const pct=eff>0?roundMi/eff*100:Infinity;const status=pct<=MARGIN*100?'ok':pct<=100?'tight':'no';
 return {eff:+eff.toFixed(1),pct:Math.round(pct),status}}
g.GCMRange={FULL_DERATE,effRange,arrival,DEFAULT,migrate,MARGIN,profiles,load,save,rangeFor,check};
if(typeof module!=='undefined')module.exports=g.GCMRange;
})(typeof window!=='undefined'?window:globalThis);
