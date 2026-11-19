#!/usr/bin/env node
// Local preview of the partner portal: serves public/ like Cloudflare Pages and answers
// /api/partner/* with the real gcm-partner Worker code on an in-memory database
// (tests/partner_worker_harness.mjs). No network calls to Cloudflare, no email leaves.
//   node scripts/partner_dev.mjs [port] [seed.json]
// The seed is { shop: {...PATCH fields}, owner, codes: [...], experiences: [...], places: [...] }.
// Prints "READY <url>" when listening. Sign in at /partner with the owner email (mock login).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { makePartner } from '../tests/partner_worker_harness.mjs';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const PUB = path.join(ROOT, 'public');
const port = Number(process.argv[2] || 8790);
const seedFile = process.argv[3];
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json', '.pbf': 'application/octet-stream' };

const regions = JSON.parse(fs.readFileSync(path.join(PUB, 'data', 'regions.json'), 'utf8'));
const partner = makePartner({ regions, env: JSON.parse(process.env.PARTNER_DEV_ENV || '{}') });

async function seed() {
  if (!seedFile) return;
  const s = JSON.parse(fs.readFileSync(seedFile, 'utf8'));
  const { owner } = await partner.seedShop({ name: s.name, slug: s.slug, region_id: s.region_id, owner: s.owner, patch: s.shop || {} });
  for (const c of s.codes || []) await partner.call('/shop/codes', { as: owner, json: c });
  for (const e of s.experiences || []) await partner.call('/shop/experiences', { as: owner, json: e });
  for (const p of s.places || []) await partner.call('/shop/places', { as: owner, json: p });
  for (const a of s.affiliates || []) await partner.call('/shop/affiliates', { as: owner, json: a });
  for (const [p, body] of s.calls || []) await partner.call(p, { as: owner, json: body });
}

function fileFor(p) {
  if (p === '/partner' || p === '/partner/') return '/partner/index.html';
  if (/^\/p(\/|$)/.test(p) && !/\.[a-z0-9]+$/i.test(p)) return '/p.html';
  if (/^\/s(\/|$)/.test(p) && !/\.[a-z0-9]+$/i.test(p) && fs.existsSync(path.join(PUB, 's.html'))) return '/s.html';
  if (p === '/' ) return '/index.html';
  if (p === '/map' || p.startsWith('/map/')) return '/index.html';
  if (!/\.[a-z0-9]+$/i.test(p) && fs.existsSync(path.join(PUB, p + '.html'))) return p + '.html';
  return p;
}

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://localhost');
  if (u.pathname.startsWith('/api/partner/')) {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const raw = Buffer.concat(chunks).toString('utf8');
    const headers = {};
    if (req.headers.cookie) headers.cookie = req.headers.cookie;
    if (req.headers['content-type']) headers['content-type'] = req.headers['content-type'];
    const r = await partner.call(u.pathname.slice('/api/partner'.length) + u.search, { method: req.method, headers, body: raw || undefined });
    const out = { 'content-type': r.headers.get('content-type') || 'application/json', 'cache-control': 'no-store' };
    const sc = r.headers.get('set-cookie');
    if (sc) out['set-cookie'] = sc.replace(/; Secure/g, '');
    res.writeHead(r.status, out);
    res.end(typeof r.body === 'string' ? r.body : JSON.stringify(r.body));
    return;
  }
  const f = path.join(PUB, fileFor(u.pathname));
  if (!f.startsWith(PUB) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end('not found'); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});

await seed();
server.listen(port, '127.0.0.1', () => console.log('READY http://127.0.0.1:' + server.address().port));
