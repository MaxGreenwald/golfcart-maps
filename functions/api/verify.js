import{stripe,json,tokenFor}from'../../lib/pay.js';
export async function onRequestGet({request,env}){
  const id=new URL(request.url).searchParams.get('session_id');if(!id||!/^cs_/.test(id))return json({error:'bad session'},400);
  try{const s=await stripe(env,'checkout/sessions/'+encodeURIComponent(id),{'expand[]':'subscription'},'GET');
    if(s.status!=='complete'||!['paid','no_payment_required'].includes(s.payment_status))return json({error:'not paid'},402);
    const t=await tokenFor(env,s.subscription);return t?json({...t,email:s.customer_details&&s.customer_details.email}):json({error:'not active'},402)}
  catch(e){return json({error:e.message},500)}}
