// Charger layer paywall ($10/yr via Stripe). Only the EV charger layer is gated.
(function(){
const K='gcm_chg_unlock',$=id=>document.getElementById(id);
const IOS=!!(window.Capacitor&&window.Capacitor.isNativePlatform&&window.Capacitor.isNativePlatform()&&window.Capacitor.getPlatform()==='ios');
const load=()=>{try{return JSON.parse(localStorage.getItem(K))}catch(_){return null}};
const save=t=>{t.at=Date.now();localStorage.setItem(K,JSON.stringify(t))};
const unlocked=()=>{const t=load();return !!(t&&t.token&&t.exp*1000>Date.now())};
function lockUI(){const b=$('cChg');if(b)b.classList.toggle('locked',!unlocked())}
async function api(p,o){const r=await fetch('/api/'+p,o);let j={};try{j=await r.json()}catch(_){}return{ok:r.ok,status:r.status,j}}
const post=b=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});
function close(){const s=$('paySheet');if(s)s.remove()}
function msg(t){const m=$('payMsg');if(m)m.textContent=t}
function sheet(){close();const d=document.createElement('div');d.id='paySheet';d.innerHTML=`<div class="pbk"></div><div class="pcard" role="dialog" aria-label="Charging stations">
<button class="px" aria-label="Close">✕</button><h3>🔌 Charging stations${IOS?'':' — $10/year'}</h3>
<p>See public EV chargers near your route, with plug types, hours and price.</p>
${IOS?'':'<button class="pbtn" id="paySub">Subscribe</button>'}
<details id="payRest"><summary>Restore purchase</summary><input id="payEmail" type="email" placeholder="Email used at checkout" autocomplete="email"><button class="pbtn2" id="payRestBtn">Restore</button></details>
<div id="payMsg" class="pmsg"></div>${IOS?'':'<div class="pfine">Renews yearly. Cancel anytime. Secure checkout by Stripe.</div>'}</div>`;
document.body.appendChild(d);d.querySelector('.pbk').onclick=close;d.querySelector('.px').onclick=close;
if(!IOS)$('paySub').onclick=async()=>{msg('Opening checkout…');const r=await api('checkout',{method:'POST'});if(r.ok&&r.j.url)location.href=r.j.url;else msg('Checkout is unavailable right now. Try again later.')};
$('payRestBtn').onclick=async()=>{const e=$('payEmail').value.trim();if(!e)return msg('Enter your email.');msg('Checking…');
 const r=await api('restore',post({email:e}));if(r.ok&&r.j.token){save(r.j);lockUI();close();window.showChg&&window.showChg(true)}
 else msg(r.status===404?'No active subscription found for that email.':'Could not check right now. Try again later.')}}
async function afterCheckout(){const q=new URLSearchParams(location.search),id=q.get('paid');if(!id)return;
 history.replaceState(null,'',location.pathname+location.hash);if(id==='cancel')return;
 const r=await api('verify?session_id='+encodeURIComponent(id));if(r.ok&&r.j.token){save(r.j);lockUI();setTimeout(()=>window.showChg&&window.showChg(true),400)}
 else{sheet();msg('We could not confirm that payment yet. Try Restore purchase in a minute.')}}
async function refresh(){const t=load();if(!t||!t.token)return;if(Date.now()-(t.at||0)<7*864e5&&t.exp*1000>Date.now())return;
 try{const r=await api('refresh',post({token:t.token}));if(r.ok&&r.j.token)save(r.j);else if(r.status===401||r.status===402)localStorage.removeItem(K)}catch(_){} lockUI()}
window.PAY={unlocked,sheet,ios:IOS};
document.addEventListener('DOMContentLoaded',()=>{lockUI();afterCheckout();refresh()});
})();
