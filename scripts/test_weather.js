// Node test for public/weather.js: thresholds, ordering, one alert per kind, quiet period, URL.
const W=require('../public/weather.js'),a=require('assert');
const J=(o)=>({hourly:Object.assign({time:['2026-10-19T13:00','2026-10-19T14:00','2026-10-19T15:00','2026-10-19T16:00'],precipitation_probability:[0,0,0,0],precipitation:[0,0,0,0],weather_code:[0,0,0,0],wind_speed_10m:[5,5,5,5],wind_gusts_10m:[8,8,8,8]},o)});
a.deepEqual(W.alerts(J({})),[]);a.deepEqual(W.alerts(null),[]);a.deepEqual(W.alerts({}),[]);
let x=W.alerts(J({precipitation_probability:[10,60,80,0],precipitation:[0,1.2,3,0]}));a.equal(x.length,1);a.equal(x[0].kind,'rain');a.match(x[0].text,/60% chance of rain around 2 PM/);
a.deepEqual(W.alerts(J({precipitation_probability:[70,0,0,0],precipitation:[0.1,0,0,0]})),[]);  // likely but a trace: no banner
x=W.alerts(J({weather_code:[0,0,95,0],wind_gusts_10m:[8,34,8,8],precipitation_probability:[0,0,90,0],precipitation:[0,0,4,0]}));
a.deepEqual(x.map(a=>a.kind),['lightning','wind','rain']);a.match(x[0].text,/3 PM/);a.match(x[1].text,/34 mph/);
a.equal(W.alerts(J({wind_speed_10m:[21,5,5,5]}))[0].kind,'wind');a.deepEqual(W.alerts(J({wind_gusts_10m:[29,29,29,29]})),[]);
a.deepEqual(W.alerts(J({weather_code:[0,0,0,0,95]})),[]);                   // beyond the 3-hour window (index 4)
const now=1e12;a.equal(W.pick(x,{lightning:now-3600e3},now).kind,'wind');   // dismissed lightning stays quiet...
a.equal(W.pick(x,{lightning:now-7*3600e3},now).kind,'lightning');            // ...for 6 hours only
a.equal(W.pick(x,{lightning:now,wind:now,rain:now},now),null);
a.match(W.url(32.8456,-117.2511),/latitude=32\.85&longitude=-117\.25&.*wind_speed_unit=mph/);a.ok(!/apikey|key=/.test(W.url(1,1)));
console.log('RESULT ALL PASS');
