import{stripe,json,check,tokenFor}from'../../lib/pay.js';
export async function onRequestPost({request,env}){
  let tok='';try{tok=(await request.json()).token}catch(_){}
  const p=await check(env,tok);if(!p)return json({error:'invalid'},401);
  try{const s=await stripe(env,'subscriptions/'+encodeURIComponent(p.sub),null,'GET');const t=await tokenFor(env,s);
    return t?json(t):json({error:'inactive'},402)}catch(e){return json({error:e.message},500)}}
