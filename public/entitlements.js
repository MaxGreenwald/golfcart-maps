// Driver plan entitlements (iOS in-app purchase via StoreKit 2; native side: ios/App/App/GCMPurchases.swift).
// One question for every feature: GCMEnt.can(feature). The core legal-roads map is NEVER gated:
// anything in CORE always returns true, and CORE and PAID may never overlap (tests/test_paywall_gate.py).
// The website is not gated at all: gating is only on inside the iOS app with the native plugin present.
(function(){
const CORE=Object.freeze(['core_map','legal_roads','road_rules','legend','legal_routing','home_town','safety_warnings']);
const PAID=Object.freeze(['extra_towns','offline_maps','voice_routing']);
const PRODUCTS=Object.freeze({monthly:'com.matchimus.golfcartmaps.driver.monthly',yearly:'com.matchimus.golfcartmaps.driver.yearly'});
const TERMS='https://www.apple.com/legal/internet-services/itunes/dev/stdeula/',PRIVACY='https://golfcartmap.com/privacy.html';
const HK='gcm-home-town';
const C=window.Capacitor;
const plugin=()=>C&&C.Plugins&&C.Plugins.GCMPurchases||null;
const gated=()=>!!(window.GCM_IOS&&plugin());
let st={paid:false,product:null,expires:null,source:'none'};
function set(s){st=Object.assign({paid:false,product:null,expires:null,source:'none'},s||{});st.paid=!!st.paid;
 window.GCM_PAID=st.paid;document.documentElement.classList.toggle('gcm-paid',st.paid);
 try{window.dispatchEvent(new CustomEvent('gcm:entitlement',{detail:Object.assign({},st)}))}catch(_){}}
function isPaid(){return st.paid}
function can(f){if(CORE.includes(f))return true;if(!PAID.includes(f))return true;if(!gated())return true;return st.paid}
function home(){try{return localStorage.getItem(HK)}catch(_){return null}}
function setHome(id){try{localStorage.setItem(HK,id)}catch(_){}}
// Your home town is always open. Other towns need the driver plan (in the app only). You can switch your home town any time,
// so every town's legal-roads map stays reachable without paying.
function canTown(id){if(!gated()||st.paid)return true;const h=home();if(!h){const cur=window.REG&&window.REG.id;setHome(cur||id);return !cur||cur===id}return h===id}
async function refresh(){const p=plugin();if(!p)return st;try{const r=await p.getEntitlement();set({paid:r.paid,product:r.product||null,expires:r.expires||null,source:'storekit'})}catch(_){}return st}
async function products(){const p=plugin();if(!p)return[];try{return(await p.getProducts({ids:[PRODUCTS.monthly,PRODUCTS.yearly]})).products||[]}catch(_){return[]}}
async function buy(id){const p=plugin();if(!p)return{ok:false};const r=await p.purchase({id});if(r&&r.paid)set({paid:true,product:r.product,expires:r.expires||null,source:'storekit'});return r}
async function restore(){const p=plugin();if(!p)return{ok:false};const r=await p.restore();await refresh();return r}
const $=id=>document.getElementById(id);
function close(){const s=$('drvSheet');if(s)s.remove()}
const NAMES={extra_towns:'More than one town',offline_maps:'Offline maps',voice_routing:'Spoken turn-by-turn directions'};
async function sheet(opts){opts=opts||{};close();const d=document.createElement('div');d.id='drvSheet';d.className='drv';
 d.innerHTML=`<div class="pbk"></div><div class="pcard" role="dialog" aria-label="Driver plan"><button class="px" aria-label="Close">✕</button>
<h3>Driver plan</h3><p>The map of legal roads, the road rules and legal routes stay open to everyone. The driver plan adds:</p>
<ul>${PAID.map(f=>`<li>${NAMES[f]}</li>`).join('')}</ul><div id="drvBtns"><div class="pmsg">Loading prices…</div></div>
${opts.town?`<button class="pbtn2" id="drvHome">Make ${opts.townName||'this town'} my town instead</button>`:''}
<button class="pbtn2" id="drvRestore">Restore purchases</button><div id="drvMsg" class="pmsg"></div>
<div class="pfine">Renews automatically until you cancel. Cancel anytime in your Apple ID settings, at least 24 hours before it renews. Payment is charged to your Apple ID. <a href="${TERMS}" target="_blank" rel="noopener">Terms of Use</a> · <a href="${PRIVACY}" target="_blank" rel="noopener">Privacy Policy</a></div></div>`;
 document.body.appendChild(d);const msg=t=>{const m=$('drvMsg');if(m)m.textContent=t};
 d.querySelector('.pbk').onclick=close;d.querySelector('.px').onclick=close;
 if(opts.town)$('drvHome').onclick=()=>{setHome(opts.town);close();opts.onUnlock&&opts.onUnlock()};
 $('drvRestore').onclick=async()=>{msg('Checking…');try{await restore()}catch(_){}if(st.paid){close();opts.onUnlock&&opts.onUnlock()}else msg('No active driver plan found for this Apple ID.')};
 const ps=await products();const b=$('drvBtns');if(!b)return;
 if(!ps.length){b.innerHTML='<div class="pmsg">The driver plan isn’t available right now. Try again later.</div>';return}
 ps.sort((x,y)=>(x.id===PRODUCTS.monthly?0:1)-(y.id===PRODUCTS.monthly?0:1));
 b.innerHTML=ps.map(p=>`<button class="pbtn" data-id="${p.id}">${p.id===PRODUCTS.yearly?'Yearly':'Monthly'}: ${p.displayPrice} / ${p.id===PRODUCTS.yearly?'year':'month'}</button>`).join('');
 b.querySelectorAll('button').forEach(x=>x.onclick=async()=>{msg('Opening the App Store…');try{const r=await buy(x.dataset.id);if(st.paid){close();opts.onUnlock&&opts.onUnlock()}else msg(r&&r.pending?'Waiting for approval.':'')}catch(_){msg('The purchase didn’t go through.')}});}
window.GCMEnt=Object.freeze({CORE,PAID,PRODUCTS,TERMS,PRIVACY,can,canTown,isPaid,state:()=>Object.assign({},st),refresh,restore,buy,products,sheet,home,setHome,_set:set,_gated:gated});
window.addEventListener('gcm:native-entitlement',e=>set(Object.assign({source:'storekit'},e.detail||{})));
set(st);if(gated())refresh();
})();
