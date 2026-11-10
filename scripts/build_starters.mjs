// Build public/data/<id>/starters.json for every live region.
// Each ride is a loop the legal-road router accepts for that vehicle (golf_cart and lsv).
// Usage: node scripts/build_starters.mjs            (every region, 45s cap each)
//        node scripts/build_starters.mjs <id> [...] (those regions, no cap)
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { placesFromPois, pickLoops } from '../lib/starters.js';

const require = createRequire(import.meta.url);
const router = require('../public/router.js');
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const rules = JSON.parse(fs.readFileSync(path.join(root, 'public/data/rules.json'), 'utf8'));
const regions = JSON.parse(fs.readFileSync(path.join(root, 'public/data/regions.json'), 'utf8'));
const only = new Set(process.argv.slice(2));

function fileFetch(url) {
  const rel = String(url || '').replace(/^\//, '');
  const p = path.join(root, 'public', rel);
  if (!fs.existsSync(p)) return { ok: false, json: async () => null };
  return { ok: true, json: async () => JSON.parse(fs.readFileSync(p, 'utf8')) };
}

async function ridesFor(region, veh, places) {
  const reg = await router.openRegion(region, rules, veh, async url => fileFetch(url));
  return pickLoops(places, stops => reg.legs(stops));
}

const want = regions.filter(r => !only.size || only.has(r.id));

// No ids: one child per region so a slow search cannot stall the rest.
if (!only.size && !process.env.STARTERS_CHILD) {
  const self = fileURLToPath(import.meta.url);
  let n = 0;
  for (const region of regions) {
    const dest = path.join(root, 'public/data', region.id, 'starters.json');
    const before = fs.existsSync(dest) ? fs.statSync(dest).mtimeMs : 0;
    const code = await new Promise(resolve => {
      const child = spawn(process.execPath, [self, region.id], {
        env: { ...process.env, STARTERS_CHILD: '1' },
        stdio: 'inherit',
      });
      const timer = setTimeout(() => { child.kill('SIGKILL'); resolve('timeout'); }, 45000);
      child.on('exit', c => { clearTimeout(timer); resolve(c); });
    });
    const wrote = fs.existsSync(dest) && fs.statSync(dest).mtimeMs > before;
    if (!wrote) {
      fs.writeFileSync(dest, JSON.stringify({ region: region.id, vehicles: { golf_cart: [], lsv: [] } }) + '\n');
      process.stdout.write(`${region.id} golf_cart=0 lsv=0 timeout\n`);
    }
    n++;
    if (code === 'timeout') process.stdout.write(`${region.id} capped at 45s\n`);
  }
  process.stdout.write(`wrote ${n} starters.json\n`);
  process.exit(0);
}

let n = 0;
for (const region of want) {
  const poisPath = path.join(root, 'public/data', region.id, 'pois.json');
  const places = fs.existsSync(poisPath) ? placesFromPois(JSON.parse(fs.readFileSync(poisPath, 'utf8'))) : [];
  const vehicles = {};
  for (const veh of ['golf_cart', 'lsv']) {
    vehicles[veh] = places.length ? await ridesFor(region, veh, places) : [];
  }
  const out = { region: region.id, vehicles };
  const dest = path.join(root, 'public/data', region.id, 'starters.json');
  fs.writeFileSync(dest, JSON.stringify(out) + '\n');
  n++;
  const g = vehicles.golf_cart.length, l = vehicles.lsv.length;
  process.stdout.write(`${region.id} golf_cart=${g} lsv=${l}\n`);
}
console.log(`wrote ${n} starters.json`);
