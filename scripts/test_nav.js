// Nav state machine with a simulated GPS track (node scripts/test_nav.js)
const N=require('../public/nav.js'),a=require('assert');
const lat0=32.80,lon0=-117.25,mLat=1/111320,mLon=1/(111320*Math.cos(lat0*Math.PI/180));
const P=(e,n)=>[lon0+e*mLon,lat0+n*mLat];
const seg=(name,pts,hw='residential',sp=25)=>{let len=0;for(let i=1;i<pts.length;i++)len+=N.hav(pts[i-1],pts[i]);return {p:pts,name,len,f:false,hw,sp}};
// north 600 m on Main St (with an unnamed straight piece in the middle), right onto Ocean Ave 500 m, left onto Palm Way 200 m
const legs=[seg('Main St',[P(0,0),P(0,300)]),seg('',[P(0,300),P(0,320)]),seg('Main St',[P(0,320),P(0,600)]),seg('Ocean Ave',[P(0,600),P(250,600),P(500,600)],'tertiary',30),seg('Palm Way',[P(500,600),P(500,800)])];
const man=N.maneuvers(legs,'golf_cart');
a.deepEqual(man.map(m=>m.type),['depart','right','left','arrive'],JSON.stringify(man.map(m=>m.text)));
a.equal(man[0].text,'Head north on Main St');a.equal(man[1].text,'Turn right onto Ocean Ave');a.ok(Math.abs(man[1].at-600)<3,man[1].at);
// unnamed continue after a named road collapses even when it is its own named run
const m2=N.maneuvers([seg('A St',[P(0,0),P(0,200)]),seg('',[P(0,200),P(0,400)]),seg('B St',[P(0,400),P(200,400)])],'lsv');
a.deepEqual(m2.map(m=>m.type),['depart','right','arrive']);a.equal(m2[0].meters,400);
a.equal(N.sayDist(152),'500 feet');a.equal(N.sayDist(15),'50 feet');a.equal(N.sayDist(1609),'1 mile');a.equal(N.sayDist(2414),'1.5 miles');
// cart speeds
a.equal(N.mph('golf_cart',{hw:'tertiary'}),17);a.equal(N.mph('golf_cart',{hw:'residential'}),12);a.equal(N.mph('lsv',{hw:'tertiary'}),23);a.equal(N.mph('lsv',{hw:'residential',sp:15}),15);
// drive the route at 7 m/s (~16 mph), 1 fix/s
function track(){const pts=[];const L=N.line(legs,'golf_cart');for(let s=0;s<=L.total+5;s+=7){let i=1;while(i<L.cum.length-1&&L.cum[i]<s)i++;const t=Math.min(1,(s-L.cum[i-1])/((L.cum[i]-L.cum[i-1])||1)),A=L.pts[i-1],B=L.pts[i];pts.push([A[0]+(B[0]-A[0])*t,A[1]+(B[1]-A[1])*t])}return pts}
let said=[],ups=[],arrived=0;const nav=new N.Navigator(legs,'golf_cart',{say:t=>said.push(t),onUpdate:i=>ups.push(i),onArrive:()=>arrived++});
nav.start();a.ok(/^Head north on Main St, then in 0.4 miles, turn right onto Ocean Ave\.$/.test(said[0]),said[0]);
let t=0;const tr=track();for(const [lon,lat] of tr){nav.update({lat,lon,t:t+=1000,speed:7})}
const iFar=said.findIndex(s=>/^In (4|5|6)\d0 feet, turn right onto Ocean Ave/.test(s)),iAt=said.indexOf('Turn right onto Ocean Ave.'),iL=said.indexOf('Turn left onto Palm Way.'),iArr=said.indexOf('You have arrived at your destination.');
a.ok(iFar>0&&iAt>iFar&&iL>iAt&&iArr>iL,JSON.stringify(said));
a.equal(said.filter(s=>s==='Turn right onto Ocean Ave.').length,1);a.equal(nav.state,'arrived');a.equal(arrived,1);
// mid-route info: remaining distance + ETA at cart speeds
const mid=ups.find(u=>u.next&&u.next.road==='Ocean Ave'&&u.toNext<300);a.ok(mid.remaining>900&&mid.remaining<1100,mid.remaining);
const etaMin=mid.remainingSec/60;a.ok(etaMin>2&&etaMin<5,etaMin);
// GPS updates after arrival are ignored
a.equal(nav.update({lat:lat0,lon:lon0,t:t+1000}),'arrived');
// off-route: drive 300 m north, then drift 60 m west for 6 s -> reroute with the new legs
said=[];let rr=0;const nav2=new N.Navigator(legs,'golf_cart',{say:x=>said.push(x),reroute:async f=>{rr++;return [seg('Side St',[[f.lon,f.lat],P(-60,600),P(0,600)]),seg('Ocean Ave',[P(0,600),P(500,600)])]}});
nav2.start();t=0;for(let n=0;n<=300;n+=7){const q=P(0,n);nav2.update({lat:q[1],lon:q[0],t:t+=1000})}
a.equal(nav2.state,'nav');
// a single bad fix (GPS jump) must not reroute
let q=P(-80,310);nav2.update({lat:q[1],lon:q[0],t:t+=1000});q=P(0,317);nav2.update({lat:q[1],lon:q[0],t:t+=1000});a.equal(rr,0);a.equal(nav2.state,'nav');
for(let k=0;k<6;k++){q=P(-60,320+k*5);nav2.update({lat:q[1],lon:q[0],t:t+=1000})}
return Promise.resolve().then(()=>new Promise(r=>setTimeout(r,10))).then(()=>{
 a.equal(rr,1);a.ok(said.includes('Off route. Rerouting.'),JSON.stringify(said));a.ok(said.includes('Route updated.'));a.equal(nav2.state,'nav');a.equal(nav2.man[0].road,'Side St');
 // failed reroute keeps trying and says so
 said=[];const nav3=new N.Navigator(legs,'lsv',{say:x=>said.push(x),reroute:async()=>null});nav3.start();t=0;for(let k=0;k<6;k++){const z=P(-100,k*5);nav3.update({lat:z[1],lon:z[0],t:t+=1000})}
 return new Promise(r=>setTimeout(r,10)).then(()=>{a.equal(nav3.state,'off');a.ok(said.some(s=>/No legal route/.test(s)));console.log('RESULT ALL PASS')})});
