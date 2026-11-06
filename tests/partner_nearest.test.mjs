// Per-experience "Start riders at their nearest stop": default on, stores off.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { nearestStart } from '../lib/partner.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const worker = readFileSync(join(root, 'workers/partner/src/index.js'), 'utf8');

test('missing value reads as on; false persists as off', () => {
  for (const v of [undefined, null, '', 1, '1', true, 'junk']) assert.equal(nearestStart(v), true, String(v));
  for (const v of [false, 0, '0', 'false']) assert.equal(nearestStart(v), false, String(v));
});

test('worker: additive column defaulting to 1, insert and patch carry it', () => {
  assert.match(worker, /ALTER TABLE experiences ADD COLUMN nearest_start INTEGER NOT NULL DEFAULT 1/);
  assert.match(worker, /nearest_start: nearestStart\(r\.nearest_start\)/);
  assert.match(worker, /INSERT INTO experiences\([^)]*nearest_start/);
  assert.match(worker, /UPDATE experiences SET[^']*nearest_start=\?/);
  assert.doesNotMatch(worker, /DROP (TABLE|COLUMN)[^\n]*experiences/);
});
