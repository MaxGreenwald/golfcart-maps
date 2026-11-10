// One-tap help: tel and sms links, location in the message, nothing sent to our servers.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { cleanPhone, phoneDisplay } from '../lib/partner.js';

const require = createRequire(import.meta.url);
const H = require('../public/help.js');

test('phone is 10 digits, links are tel and sms, location is in the text', () => {
  assert.equal(cleanPhone('858-555-0100').value, '8585550100');
  assert.equal(cleanPhone('1 (858) 555-0100').value, '8585550100');
  assert.equal(cleanPhone('').value, '');
  assert.match(cleanPhone('555').error, /10-digit/);
  assert.equal(phoneDisplay('8585550100'), '(858) 555-0100');
  assert.equal(H.digits('858-555-0100'), '18585550100');
  assert.equal(H.telHref('8585550100'), 'tel:+18585550100');
  const body = H.message(32.798, -117.2466);
  assert.match(body, /32\.79800, -117\.24660/);
  assert.match(body, /https:\/\/maps\.apple\.com\/\?ll=32\.79800,-117\.24660/);
  assert.equal(body.includes('\u2014'), false);
  const sms = H.smsHref('8585550100', body);
  assert.ok(sms.startsWith('sms:+18585550100?body='));
  assert.match(decodeURIComponent(sms.split('body=')[1]), /32\.79800/);
  assert.match(H.message(null, null), /do not have a location/);
});

test('help.js does not send the location anywhere', () => {
  const src = fs.readFileSync(new URL('../public/help.js', import.meta.url), 'utf8');
  assert.equal(src.includes('fetch('), false);
  assert.equal(src.includes('GCMTrack'), false);
  assert.equal(src.includes('\u2014'), false);
});

test('CarPlay help() returns call and text links with the fix', () => {
  const help = fs.readFileSync(new URL('../public/help.js', import.meta.url), 'utf8');
  const src = fs.readFileSync(new URL('../public/carplay.js', import.meta.url), 'utf8');
  const access = JSON.stringify({
    slug: 'beachmode', code: 'TEST', at: Date.now(),
    shop: { name: 'Beach Mode', phone: '8585550100' },
    experiences: [],
  });
  const store = { gcm_partner_access: access };
  const ls = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
  const win = {};
  const ctx = { window: win, self: win, localStorage: ls, console, Promise, JSON, Math, Date, isFinite, String, Number, encodeURIComponent };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(help, ctx);
  vm.runInContext(src, ctx);
  const r = win.GCMCarPlay.help(32.8, -117.25);
  assert.equal(r.ok, true);
  assert.equal(r.tel, 'tel:+18585550100');
  assert.match(r.body, /32\.80000, -117\.25000/);
  assert.ok(r.sms.startsWith('sms:+18585550100?body='));
  store.gcm_partner_access = JSON.stringify({ slug: 'x', at: Date.now(), shop: { name: 'X' }, experiences: [] });
  assert.equal(win.GCMCarPlay.help(1, 2).ok, false);
});
