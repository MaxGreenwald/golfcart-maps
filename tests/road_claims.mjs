// Per road name: miles by class for each vehicle, using public/roadrule.js (the map's own rule).
// node tests/road_claims.mjs <region id>  ->  {"<name>": {"mi":..,"lsv":[posted,assumed,red],"golf_cart":[...]}, ...}
import fs from 'fs'; import path from 'path'; import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const P = path.join(path.dirname(new URL(import.meta.url).pathname), '..', 'public');
const R = require(path.join(P, 'roadrule.js'));
const rules = JSON.parse(fs.readFileSync(path.join(P, 'data/rules.json')));
const id = process.argv[2]; const g = JSON.parse(fs.readFileSync(path.join(P, 'data/regions.json'))).find(r => r.id === id);
const D = JSON.parse(fs.readFileSync(path.join(P, `data/${id}/index.json`)));
const RV = { golf_cart: R.ruleFor(rules, g, 'golf_cart'), lsv: R.ruleFor(rules, g, 'lsv') };
const ft = (a, b) => { const r = Math.PI / 180, dl = (b[1] - a[1]) * r, dn = (b[0] - a[0]) * r, x = Math.sin(dl / 2) ** 2 + Math.cos(a[1] * r) * Math.cos(b[1] * r) * Math.sin(dn / 2) ** 2; return 20902231 * 2 * Math.asin(Math.sqrt(x)); };
const out = {}; let cartNonPath = 0;
for (const f of fs.readdirSync(path.join(P, `data/${id}/tiles`))) for (const s of JSON.parse(fs.readFileSync(path.join(P, `data/${id}/tiles/${f}`)))) {
  const n = D.names[s[0]] || ''; let L = 0; for (let i = 1; i < s[7].length; i++) L += ft(s[7][i - 1], s[7][i]); L /= 5280;
  const o = out[n] = out[n] || { mi: 0, lsv: [0, 0, 0], golf_cart: [0, 0, 0] }; o.mi += L;
  for (const v of ['lsv', 'golf_cart']) { const c = R.cls(s, RV[v]); o[v][c === 3 ? 2 : c] += L; if (v === 'golf_cart' && c !== 3 && s[3] !== 'c' && s[3] !== 'd') cartNonPath += L; }
}
process.stdout.write(JSON.stringify({ roads: out, golf_cart_open_street_mi: cartNonPath, rules: RV }));
