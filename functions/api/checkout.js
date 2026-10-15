import{stripe,json}from'../../lib/pay.js';
export async function onRequestPost({request,env}){
  try{const o=new URL(request.url).origin;
    const pr=await stripe(env,'prices',{'lookup_keys[]':'charger_map_yearly',active:'true'},'GET');
    const price=env.STRIPE_PRICE_ID||(pr.data[0]&&pr.data[0].id);if(!price)return json({error:'no price'},500);
    const s=await stripe(env,'checkout/sessions',{mode:'subscription','managed_payments[enabled]':'false','line_items[0][price]':price,'line_items[0][quantity]':1,
      success_url:o+'/?paid={CHECKOUT_SESSION_ID}',cancel_url:o+'/?paid=cancel',allow_promotion_codes:'true'});
    return json({url:s.url})}catch(e){return json({error:e.message},500)}}
