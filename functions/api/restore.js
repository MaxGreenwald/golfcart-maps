import{json,tokenFor,activeSubForEmail}from'../../lib/pay.js';
// NOTE abuse risk: anyone who knows a subscriber's email can unlock this layer. Acceptable for a $10 test
// on public data; replace with an emailed magic link before relying on it.
export async function onRequestPost({request,env}){
  let email='';try{email=String((await request.json()).email||'').trim().toLowerCase()}catch(_){}
  if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))return json({error:'bad email'},400);
  try{const t=await tokenFor(env,await activeSubForEmail(env,email));return t?json(t):json({error:'none'},404)}
  catch(e){return json({error:e.message},500)}}
