// Rules quiz before the renter map unlocks. Questions come from the same road rule the map uses
// (roadrule.ruleFor), so the quiz can never say a road is legal when the map says it isn't.
// Shared by the renter page (window.GCMQuiz) and the partner Worker (which re-grades and records).
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMQuiz = api;
})(typeof self !== 'undefined' ? self : this, function () {
  const VERSION = 1;
  const PASS_DAYS = 1;
  const KEY = 'gcm_quiz_pass';

  // Stable order that is not "right answer first": rotate by a hash of the question id.
  function arrange(id, opts) {
    let h = 0;
    for (const ch of String(id)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    const k = h % opts.length;
    return opts.slice(k).concat(opts.slice(0, k));
  }
  function q(id, text, right, wrong) {
    const rows = arrange(id, [{ right: true, text: right }, ...wrong.map(t => ({ right: false, text: t }))]);
    const options = rows.map((r, i) => ({ id: 'o' + i, text: r.text }));
    return { id, text, options, answer: options[rows.findIndex(r => r.right)].id };
  }

  /**
   * build({ rule, vehicle, shopRules }) -> [{ id, text, options: [{id,text}], answer }]
   * rule: roadrule.ruleFor(...) for the shop's region and vehicle, or null when unknown.
   */
  function build(o) {
    o = o || {};
    const R = o.rule || null;
    const cart = o.vehicle === 'lsv' ? 'this LSV' : 'this cart';
    const out = [];
    if (R && R.not_street_legal) {
      out.push(q('roads', `Where can you drive ${cart} here?`, 'Only on cart paths', ['On any road posted 25 mph or less', 'On any road']));
    } else if (R && +R.max_posted > 0) {
      const n = +R.max_posted;
      out.push(q('speed', `What is the fastest posted speed limit you may drive ${cart} on here?`,
        n + ' mph', [(n + 10) + ' mph', 'Any speed limit']));
    }
    if (R && R.designated_only && !R.not_street_legal) {
      out.push(q('designated', 'Which roads are allowed?', 'Only cart paths and roads marked for carts', ['Any quiet street', 'Any road under the speed limit above']));
    }
    if (R && R.daylight_only) {
      out.push(q('daylight', `When can you drive ${cart}?`, 'In daylight only', ['Any time', 'Only after dark']));
    }
    out.push(q('red', 'What do red roads on the map mean?', `Off limits for ${cart}`, ['A faster way to go', 'Heavy traffic right now']));
    out.push(q('signs', 'The map and a posted sign disagree. Which do you follow?', 'The posted sign', ['The map', 'Whichever is faster']));
    const own = String(o.shopRules || '').trim();
    if (own) out.push({ id: 'shop', text: 'The shop\u2019s rules: ' + own, options: [{ id: 'o0', text: 'I read the shop\u2019s rules and will follow them' }], answer: 'o0' });
    return out;
  }

  /** { ok, wrong: [question ids] }. Every question must be answered right. */
  function grade(questions, answers) {
    const a = answers || {};
    const wrong = (questions || []).filter(x => a[x.id] !== x.answer).map(x => x.id);
    return { ok: wrong.length === 0, wrong };
  }

  // Device record so a renter takes it once a day per code. The shop's record is on the server.
  function passKey(slug, code) { return String(slug || '').toLowerCase() + ':' + String(code || '').toUpperCase(); }
  function passed(store, slug, code, now) {
    try {
      const all = JSON.parse(store.getItem(KEY) || '{}');
      const t = all[passKey(slug, code)];
      return !!t && (now || Date.now()) - t < PASS_DAYS * 864e5;
    } catch (e) { return false; }
  }
  function markPassed(store, slug, code, now) {
    try {
      const all = JSON.parse(store.getItem(KEY) || '{}');
      all[passKey(slug, code)] = now || Date.now();
      store.setItem(KEY, JSON.stringify(all));
    } catch (e) {}
  }

  return { VERSION, PASS_DAYS, build, grade, passed, markPassed };
});
