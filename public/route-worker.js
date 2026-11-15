// Route search off the main thread. Classic worker (importScripts) so the website
// and the Capacitor iOS web view can both start it. The page posts road tiles;
// this file never touches the DOM.
importScripts('roadrule.js', 'router.js');

let D = { segs: [] };
let net = GCMRouter.create();
let searchToken = 0;
const inbox = [];
let busy = false;

function ack(msg, extra) {
  postMessage(Object.assign({ type: 'ack', id: msg.id }, extra || {}));
}

function applyAdd(msg) {
  if (msg.reset) {
    D = { segs: [] };
    net = GCMRouter.create();
  }
  const built = GCMRouter.graphOpts(msg.rule, msg.regionId, msg.lenient);
  const segs = msg.segs || [];
  for (let i = 0; i < segs.length; i++) D.segs[msg.from + i] = segs[i];
  net.build(D, msg.from, { cls: built.cls, unk: built.unk, rule: built.rule, to: msg.from + segs.length });
  ack(msg);
}

function pump() {
  if (busy) return;
  const msg = inbox.shift();
  if (!msg) return;
  if (msg.type === 'search') {
    busy = true;
    runSearch(msg).then(() => { busy = false; pump(); }, () => { busy = false; pump(); });
    return;
  }
  if (msg.type === 'reset') {
    D = { segs: [] };
    net = GCMRouter.create();
    ack(msg);
  } else if (msg.type === 'add') applyAdd(msg);
  pump();
}

function runSearch(msg) {
  const token = ++searchToken;
  const stat = {};
  return net.astarAsync(msg.s, msg.t, {
    risky: !!msg.risky,
    rule: msg.rule,
    riskyMax: msg.riskyMax,
    backSeg: msg.backSeg,
    deadline: msg.deadline,
    stateBudget: msg.stateBudget,
    stat,
    stop: () => token !== searchToken,
  }).then(parts => {
    postMessage({ type: 'result', id: msg.id, parts: token === searchToken ? parts : null, stat, cancelled: token !== searchToken });
  }).catch(err => {
    postMessage({ type: 'result', id: msg.id, error: String(err && err.message || err), stat });
  });
}

onmessage = (e) => {
  const msg = e.data || {};
  if (msg.type === 'search' || msg.type === 'add' || msg.type === 'reset') {
    inbox.push(msg);
    pump();
  }
};
