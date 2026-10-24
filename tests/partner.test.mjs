import { assertShopSlug, normalizeSlug, SYSTEM_SLUGS, randomCode, couponCode } from '../lib/partner.js';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const regions = JSON.parse(readFileSync(join(root, 'public/data/regions.json'), 'utf8'));
const citySlugs = regions.map(r => r.slug);

let failed = 0;
function ok(name, cond) { if (!cond) { console.error('FAIL', name); failed++; } else console.log('ok', name); }

ok('normalize', normalizeSlug(' La Jolla Cart! ') === 'la-jolla-cart');
ok('good slug', assertShopSlug('lajollacartco', citySlugs).ok);
ok('reject sandiego', !assertShopSlug('sandiego', citySlugs).ok);
ok('reject map', !assertShopSlug('map', citySlugs).ok);
ok('system has partner', SYSTEM_SLUGS.has('partner'));
const c = randomCode(4);
ok('code length', c.length >= 6);
ok('code alphabet', /^[0-9A-HJKMNP-TV-Z]+$/.test(c));
ok('coupon2', couponCode('OFFER').startsWith('OFFER-'));

if (failed) { console.error(failed, 'failed'); process.exit(1); }
console.log('ALL PASS');
