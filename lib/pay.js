// Shared helpers for the charger paywall (Cloudflare Pages Functions).
const API='https://api.stripe.com/v1/';
export async function stripe(env,path,params,method){
  const opt={method:method||(params?'POST':'GET'),headers:{Authorization:'Bearer '+env.STRIPE_SECRET_KEY}};
  let url=API+path;
  if(params){const b=new URLSearchParams();for(const[k,v]of Object.entries(params))if(v!=null)b.append(k,v);
    if(opt.method==='GET')url+=(url.includes('?')?'&':'?')+b;else{opt.body=b;opt.headers['Content-Type']='application/x-www-form-urlencoded'}}
  const r=await fetch(url,opt);const j=await r.json();if(!r.ok)throw new Error((j.error&&j.error.message)||('stripe '+r.status));return j}
export const json=(o,s=200)=>new Response(JSON.stringify(o),{status:s,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
const b64u=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const ub64=s=>atob(s.replace(/-/g,'+').replace(/_/g,'/'));
async function key(env){return crypto.subtle.importKey('raw',new TextEncoder().encode(env.UNLOCK_SIGNING_SECRET),{name:'HMAC',hash:'SHA-256'},false,['sign'])}
async function sig(env,body){return b64u(await crypto.subtle.sign('HMAC',await key(env),new TextEncoder().encode(body)))}
export async function sign(env,payload){const body=b64u(new TextEncoder().encode(JSON.stringify(payload)));return body+'.'+await sig(env,body)}
export async function check(env,token){
  if(!token||!token.includes('.'))return null;const[body,s]=token.split('.');
  if(s!==await sig(env,body))return null;let p;try{p=JSON.parse(ub64(body))}catch(_){return null}
  if(!p.exp||p.exp*1000<Date.now())return null;return p}
const ACTIVE=['active','trialing'];
export const periodEnd=sub=>sub.current_period_end||(sub.items&&sub.items.data[0]&&sub.items.data[0].current_period_end)||Math.floor(Date.now()/1000)+86400;
// Token lasts until the paid period ends; client re-checks /api/refresh weekly so a cancel is noticed.
export async function tokenFor(env,sub){if(!sub||!ACTIVE.includes(sub.status))return null;const exp=periodEnd(sub);
  return{token:await sign(env,{sub:sub.id,exp}),exp}}
export async function activeSubForEmail(env,email){
  const cs=await stripe(env,'customers',{email,limit:10},'GET');
  for(const c of cs.data){const ss=await stripe(env,'subscriptions',{customer:c.id,status:'all',limit:10},'GET');
    const s=ss.data.find(x=>ACTIVE.includes(x.status));if(s)return s}
  return null}
