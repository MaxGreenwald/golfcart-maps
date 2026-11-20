// Spanish renter page (public/i18n.js): language pick, exact lines, patterns, real nav step text,
// and the DOM swap that leaves the shop's own words alone and switches back to English.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const L = require('../public/i18n.js');
const N = require('../public/nav.js');
const R = require('../public/reminders.js');

test('language: ?lang wins, then the saved choice, then the phone language', () => {
  assert.equal(L.pick('?lang=es', 'en', 'en-US'), 'es');
  assert.equal(L.pick('?code=X&lang=en', 'es', 'es-MX'), 'en');
  assert.equal(L.pick('', 'es', 'en-US'), 'es');
  assert.equal(L.pick('', null, 'es-MX'), 'es');
  assert.equal(L.pick('', null, 'en-US'), 'en');
  assert.equal(L.pick('', null, 'est'), 'en');
});

test('exact lines and patterns keep the spacing around them', () => {
  assert.equal(L.es('Unlock'), 'Desbloquear');
  assert.equal(L.es('  Experiences '), '  Experiencias ');
  assert.equal(L.es(' unlocked Beach Mode. Pick a ride, then start from where you are.'), ' desbloqueó Beach Mode. Elige un paseo y empieza desde donde estás.');
  assert.equal(L.es('1 stop'), '1 parada');
  assert.equal(L.es('4 stops'), '4 paradas');
  assert.equal(L.es('Head back in 12 minutes.'), 'Regresa en 12 minutos.');
  assert.equal(L.es('Green roads are legal for a golf cart. Red roads are off limits. The blue line is your route.'),
    'Las calles verdes son legales para un carrito de golf. Las rojas están prohibidas. La línea azul es tu ruta.');
  assert.equal(L.es('Seal Rock Café'), 'Seal Rock Café', 'unknown text is left alone');
});

test('no Spanish line uses an em dash, and every reminder nudge has Spanish', () => {
  for (const v of Object.values(L.DICT)) assert.ok(!v.includes('\u2014'), v);
  const lines = [];
  const now = new Date(2026, 10, 19, 16, 0);
  for (const travelMin of [0, 20, 29, 90]) for (const n of [R.timeNudge({ now, returnBy: '16:30', travelMin })]) if (n) lines.push(n.text);
  lines.push(R.timeNudge({ now, returnBy: '15:30', travelMin: 0 }).text);
  for (const [homeMi, batteryPct] of [[5, 0], [5, 10], [5, 60]]) { const n = R.rangeNudge({ rangeMi: 10, homeMi, batteryPct }); if (n) lines.push(n.text); }
  const ids = new Set(lines);
  assert.ok(ids.size >= 7, 'covers every nudge kind: ' + [...ids].join(' | '));
  for (const line of lines) assert.notEqual(L.es(line), line, 'untranslated nudge: ' + line);
});

test('real turn-by-turn text from nav.js comes out in Spanish', () => {
  const runs = [
    { name: 'Coast Blvd', points: [[32.8500, -117.2700], [32.8510, -117.2700], [32.8520, -117.2700]] },
    { name: 'Prospect St', points: [[32.8520, -117.2700], [32.8520, -117.2690], [32.8520, -117.2680]] },
    { name: 'Girard Ave', points: [[32.8520, -117.2680], [32.8510, -117.2680], [32.8500, -117.2680]] },
  ];
  for (const [dest, opts] of [['Seal Rock', {}], ['', {}], ['Seal Rock', { continuing: true }]]) {
    const r = N.buildSteps(runs, dest, opts);
    assert.ok(r.steps.length >= 3);
    for (const st of r.steps) {
      assert.notEqual(L.es(st.text), st.text, 'untranslated step: ' + st.text);
      const spoken = N.phrase(st, 200);
      assert.notEqual(L.es(spoken), spoken, 'untranslated spoken line: ' + spoken);
    }
  }
  assert.equal(L.es('Turn right onto Prospect St'), 'Gira a la derecha en Prospect St');
  assert.equal(L.es('In 0.2 mi, turn left onto Girard Ave'), 'En 0.2 mi, gira a la izquierda en Girard Ave');
  assert.equal(L.es('Then turn left onto Girard Ave in 500 ft'), 'Luego, gira a la izquierda en Girard Ave en 500 ft');
});

test('route notes, arrival lines and every road-rule message come out fully in Spanish', () => {
  const Rule = require('../public/roadrule.js');
  const ENGLISH = /\b(the|your|you|and|roads?|only|stops?|route|from|there|this|street-legal|cart|paths?)\b/i;
  const lines = [
    'You’ve arrived at Seal Rock. Next stop: Cove Beach.', 'You’ve arrived at the stop.',
    'Location is off. Turn it on to start from you. This route starts from the middle of the map.',
    'Location is off. Turn it on to start from you. This short hop starts from the middle of the map.',
    'Location is off, and there’s no legal golf cart road from the middle of the map to the first stop. Turn on location, or follow the pins.',
    '2.1 mi · ⚠️ 2 risky stretches (red dashes). Use caution.', '0.8 mi on legal golf cart roads.',
    'Follows legal golf cart roads. A hop off that network is left open.', 'The line follows legal street-legal LSV roads.',
  ];
  for (const r of [{ veh: 'golf_cart', max_posted: 25 }, { veh: 'lsv', max_posted: 35 }, { veh: 'golf_cart', not_street_legal: true }, { veh: 'golf_cart', designated_only: true }]) {
    for (const o of [{}, { risky: true }, { reason: 'timeout' }]) lines.push(Rule.routeStop(r, o));
    lines.push(Rule.noRoute(r));
  }
  for (const line of lines) {
    const es = L.es(line);
    assert.ok(!ENGLISH.test(es.replace(/Seal Rock|Cove Beach|LSV/g, '')), `English left in: ${line} -> ${es}`);
  }
  assert.equal(L.es('You’ve arrived at Seal Rock. Next stop: Cove Beach.'), 'Llegaste a Seal Rock. Siguiente parada: Cove Beach.');
});
