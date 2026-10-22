// regions.js: the city picker list. Sorted A-Z by display name at render time, so new regions in
// data/regions.json always land in order (regions.json itself keeps San Diego first: it's the default
// and REGIONS[0] fallback). Used by app.js (the city chip in the top row) and the Node test tests/test_city_order.py.
(function(root){
const label=r=>r.short||r.name||r.id;
const byName=(a,b)=>label(a).localeCompare(label(b),'en',{sensitivity:'base',numeric:true})||String(a.id).localeCompare(String(b.id));
// regions: the regions.json list; keepId: a hidden region opened by link (?r=) stays selectable; ios: no "(beta)" tags in the App Store build
function pickerList(regions,keepId,ios){return (regions||[]).filter(r=>!r.hidden||r.id===keepId).slice().sort(byName).map(r=>({id:r.id,text:label(r)}))}
const api={pickerList,label,byName};
if(typeof module==='object'&&module.exports)module.exports=api;else root.GCMRegions=api;
})(typeof window!=='undefined'?window:globalThis);
