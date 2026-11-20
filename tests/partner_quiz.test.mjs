// Rules quiz: questions from the same road rule the map uses, all-right grading, and the
// partner Worker's re-grade plus pass record (code and time). Runs the real partner Worker.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { makePartner } from './partner_worker_harness.mjs';

const require = createRequire(import.meta.url);
const Q = require('../public/quiz.js');
const RR = require('../public/roadrule.js');
const rules = JSON.parse(readFileSync(new URL('../public/data/rules.json', import.meta.url)));
const regions = JSON.parse(readFileSync(new URL('../public/data/regions.json', import.meta.url)));
const rightAnswers = qs => Object.fromEntries(qs.map(q => [q.id, q.answer]));

test('questions follow the region rule: speed cap, designated roads, daylight, red roads, signs, shop rules', () => {
  const sd = regions.find(r => r.id === 'sd');
  const gs = regions.find(r => r.id === 'gulfshores');
  const cart = Q.build({ rule: RR.ruleFor(rules, gs, 'golf_cart'), vehicle: 'golf_cart', shopRules: 'Drivers 16 and up.' });
  const speed = cart.find(q => q.id === 'speed');
  const capped = RR.ruleFor(rules, gs, 'golf_cart').max_posted;
  assert.equal(speed.options.find(o => o.id === speed.answer).text, capped + ' mph');
  assert.ok(cart.some(q => q.id === 'red') && cart.some(q => q.id === 'signs'));
  assert.equal(cart.at(-1).id, 'shop');
  assert.match(cart.at(-1).text, /Drivers 16 and up\./);
  const lsv = Q.build({ rule: RR.ruleFor(rules, sd, 'lsv'), vehicle: 'lsv' });
  assert.match(lsv[0].text, /this LSV/);
  assert.equal(lsv[0].options.find(o => o.id === lsv[0].answer).text, RR.ruleFor(rules, sd, 'lsv').max_posted + ' mph');
  const fl = Q.build({ rule: { max_posted: 35, designated_only: true, daylight_only: true, veh: 'golf_cart' }, vehicle: 'golf_cart' });
  assert.deepEqual(fl.map(q => q.id), ['speed', 'designated', 'daylight', 'red', 'signs']);
  const banned = Q.build({ rule: { not_street_legal: true, max_posted: 0 }, vehicle: 'golf_cart' });
  assert.equal(banned[0].id, 'roads');
  assert.equal(banned[0].options.find(o => o.id === banned[0].answer).text, 'Only on cart paths');
  // No rule on file: no made-up speed question.
  assert.deepEqual(Q.build({ rule: null }).map(q => q.id), ['red', 'signs']);
  // The right answer is not always first and option ids don't give it away.
  const firsts = fl.filter(q => q.options[0].id === q.answer).length;
  assert.ok(firsts < fl.length);
  for (const q of fl) for (const o of q.options) assert.match(o.id, /^o\d$/);
  for (const q of cart.concat(fl, banned)) assert.doesNotMatch(q.text + q.options.map(o => o.text).join(''), /\u2014/);
});

test('grading needs every answer right; the device remembers a pass for a day', () => {
  const qs = Q.build({ rule: { max_posted: 25 } });
  assert.deepEqual(Q.grade(qs, rightAnswers(qs)), { ok: true, wrong: [] });
  const one = { ...rightAnswers(qs), red: 'o9' };
  assert.deepEqual(Q.grade(qs, one).wrong, ['red']);
  assert.equal(Q.grade(qs, {}).wrong.length, qs.length);
  const store = new Map();
  const ls = { getItem: k => store.get(k) ?? null, setItem: (k, v) => store.set(k, v) };
  const t = Date.UTC(2026, 10, 19, 18);
  assert.equal(Q.passed(ls, 'beachmode', 'ab12', t), false);
  Q.markPassed(ls, 'BeachMode', 'ab12', t);
  assert.equal(Q.passed(ls, 'beachmode', 'AB12', t + 3600e3), true);
  assert.equal(Q.passed(ls, 'beachmode', 'AB12', t + 25 * 3600e3), false);
  assert.equal(Q.passed(ls, 'beachmode', 'OTHER', t), false);
});

test('worker: the shop turns the quiz on; a renter pass is re-graded and recorded with code and time', async () => {
  const p = makePartner({ regions });
  const { owner } = await p.seedShop({ patch: { vehicle: 'golf_cart', rental: { rules: 'Seat belts on.' } } });
  await p.call('/shop/codes', { as: owner, json: { code: 'CART7', multi_use: true } });
  const off = await p.call('/public/lajollacartco/unlock?code=CART7');
  assert.equal(off.body.shop.quiz_on, false);
  const on = await p.call('/shop', { as: owner, method: 'PATCH', json: { quiz_on: true } });
  assert.equal(on.status, 200, JSON.stringify(on.body));
  const u = await p.call('/public/lajollacartco/unlock?code=CART7');
  assert.equal(u.body.shop.quiz_on, true);
  const admin = await p.call('/shop/quiz', { as: owner });
  assert.equal(admin.status, 200, JSON.stringify(admin.body));
  assert.equal(admin.body.on, true);
  const qs = admin.body.questions;
  const sd = regions.find(r => r.id === 'sd');
  assert.deepEqual(qs, Q.build({ rule: RR.ruleFor(rules, sd, 'golf_cart'), vehicle: 'golf_cart', shopRules: 'Seat belts on.' }), 'same quiz as the renter page builds');
  const bad = await p.call('/public/lajollacartco/quiz', { json: { code: 'cart7', answers: { ...rightAnswers(qs), signs: 'o9' } } });
  assert.equal(bad.status, 400);
  assert.deepEqual(bad.body.wrong, ['signs']);
  const ok = await p.call('/public/lajollacartco/quiz', { json: { code: 'cart7', answers: rightAnswers(qs) } });
  assert.equal(ok.status, 200, JSON.stringify(ok.body));
  assert.ok(ok.body.passed_at > 0);
  const passes = (await p.call('/shop/quiz', { as: owner })).body.passes;
  assert.equal(passes.length, 1);
  assert.equal(passes[0].code, 'CART7');
  assert.equal(passes[0].questions, qs.length);
  assert.equal((await p.call('/public/lajollacartco/quiz', { json: { code: 'NOPE1', answers: rightAnswers(qs) } })).status, 403);
  assert.equal((await p.call('/shop/quiz')).status, 401);
});
