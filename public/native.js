// Native-app (Capacitor) layer. Loaded before pay.js/app.js so they can read window.GCM_IOS.
// App Store rules for the iOS build (the website is unchanged):
//  - 3.1.1: no Stripe paywall / restore and no Venmo tip link inside the iOS app (digital unlocks must use IAP).
//  - 2.2: no "beta" labels inside the iOS app (Apple rejects apps presented as betas).
// Native features: share sheet (@capacitor/share) and haptics (@capacitor/haptics).
(function(){
const C=window.Capacitor,NATIVE=!!(C&&C.isNativePlatform&&C.isNativePlatform()),IOS=NATIVE&&C.getPlatform&&C.getPlatform()==='ios';
window.GCM_NATIVE=NATIVE;window.GCM_IOS=IOS;
if(IOS)document.documentElement.classList.add('ios-app');
function plug(n,m,o){try{const p=C&&C.Plugins&&C.Plugins[n];if(p&&typeof p[m]==='function')return Promise.resolve(p[m](o));if(C&&C.nativePromise)return C.nativePromise(n,m,o)}catch(e){return Promise.reject(e)}return Promise.reject(new Error('no '+n))}
window.gcmPlug=plug;
// kind: 'warn' (route uses a risky stretch) or 'ok'
window.gcmHaptic=kind=>{if(!NATIVE)return;(kind==='warn'?plug('Haptics','notification',{type:'WARNING'}):plug('Haptics','impact',{style:'LIGHT'})).catch(()=>{})};
window.gcmCanShare=()=>NATIVE||!!navigator.share;
// Returns 'shared' | 'copied' | false
window.gcmShare=async o=>{
 if(NATIVE){try{await plug('Share','share',{title:o.title,text:o.text,url:o.url,dialogTitle:o.title});return 'shared'}catch(e){if(e&&/cancel/i.test(e.message||''))return false}}
 if(navigator.share){try{await navigator.share({title:o.title,text:o.text,url:o.url});return 'shared'}catch(e){return false}}
 try{await navigator.clipboard.writeText(o.url);return 'copied'}catch(e){return false}};
})();
