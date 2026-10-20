// weather.js: rain / lightning / high-wind alerts for the route area from Open-Meteo (free, no key, no account).
// Pure parts (url, alerts, quiet) are shared with scripts/test_weather.js. The app shows ONE banner for the most
// serious alert in the next 3 hours, and a dismissed alert stays quiet for 6 hours (no nagging).
(function(root){
const TH={rainProb:50,rainMm:0.5,gust:30,wind:20},HOURS=3,QUIET_MS=6*3600e3,CACHE_MS=30*60e3;
const STORM=new Set([95,96,99]),RAINC=new Set([61,63,65,66,67,80,81,82]);
function url(lat,lon){return `https://api.open-meteo.com/v1/forecast?latitude=${(+lat).toFixed(2)}&longitude=${(+lon).toFixed(2)}&hourly=precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m&wind_speed_unit=mph&forecast_hours=${HOURS+1}&timezone=auto`}
const hr=t=>{const h=+String(t).slice(11,13);return (h%12||12)+(h<12?' AM':' PM')};
// j: Open-Meteo JSON; returns [{kind,level,title,text,at}] sorted most serious first (lightning > wind > rain)
function alerts(j){const H=j&&j.hourly;if(!H||!Array.isArray(H.time))return [];const n=Math.min(H.time.length,HOURS+1),out=[];
 const g=(k,i)=>H[k]&&H[k][i]!=null?+H[k][i]:null;
 for(let i=0;i<n;i++){const wc=g('weather_code',i),t=H.time[i];
  if(STORM.has(wc)&&!out.some(a=>a.kind==='lightning')){out.push({kind:'lightning',level:3,at:t,title:'⚡ Thunderstorms nearby',text:`Lightning is possible around ${hr(t)}. Golf carts give no lightning protection; wait it out indoors.`})}
  const gu=g('wind_gusts_10m',i),ws=g('wind_speed_10m',i);
  if(((gu!=null&&gu>=TH.gust)||(ws!=null&&ws>=TH.wind))&&!out.some(a=>a.kind==='wind')){out.push({kind:'wind',level:2,at:t,title:'💨 High wind',text:`Gusts up to ${Math.round(Math.max(gu||0,ws||0))} mph around ${hr(t)}. Hold on to hats and canopies, and drive slowly.`})}
  const pp=g('precipitation_probability',i),mm=g('precipitation',i);
  if(((pp!=null&&pp>=TH.rainProb&&(mm==null||mm>=TH.rainMm))||RAINC.has(wc))&&!out.some(a=>a.kind==='rain')){out.push({kind:'rain',level:1,at:t,title:'🌧️ Rain likely',text:`${pp!=null?pp+'% chance of rain':'Rain'} around ${hr(t)}. Roads get slick and most carts have no doors.`})}}
 return out.sort((a,b)=>b.level-a.level)}
// dismissed: {kind: timestamp}; an alert is quiet if dismissed within QUIET_MS
const quiet=(a,dismissed,now)=>!!(dismissed&&dismissed[a.kind]&&now-dismissed[a.kind]<QUIET_MS);
function pick(list,dismissed,now){return (list||[]).find(a=>!quiet(a,dismissed,now))||null}
const api={url,alerts,pick,quiet,TH,HOURS,QUIET_MS,CACHE_MS};
if(typeof module==='object'&&module.exports)module.exports=api;else root.GCMWeather=api;
})(typeof window!=='undefined'?window:globalThis);
