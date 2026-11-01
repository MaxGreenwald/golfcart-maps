// Turn-by-turn maneuvers (public/nav.js): turn side, distance phrasing, off-route, arrival.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const N = require('../public/nav.js');

// South on Ingraham, right (west) onto Garnet, then left (south) onto Mission.
const runs = [
  { name: 'Ingraham St', points: [[32.800, -117.240], [32.799, -117.240], [32.798, -117.240]] },
  { name: 'Ingraham St', points: [[32.798, -117.240]] },
  { name: 'Garnet Ave', points: [[32.798, -117.240], [32.798, -117.242], [32.798, -117.244]] },
  { name: 'Mission Blvd', points: [[32.798, -117.244], [32.797, -117.244]] },
];
const r = N.buildSteps(runs, 'Crystal Pier');

test('steps: depart, right onto Garnet, left onto Mission, arrive', () => {
  assert.deepEqual(r.steps.map(s => s.text), [
    'Head south on Ingraham St', 'Turn right onto Garnet Ave', 'Turn left onto Mission Blvd', 'Arrive at Crystal Pier']);
  assert.equal(r.steps[1].mod, 'right');
  assert.equal(r.steps[2].mod, 'left');
});

test('live status: distance before the turn counts down and names the street', () => {
  const a = N.status(r, [32.7995, -117.24]);
  const b = N.status(r, [32.7983, -117.24]);
  assert.match(a.text, /^In \d+ ft, turn right onto Garnet Ave$/);
  assert.ok(b.toNext < a.toNext);
  const c = N.status(r, [32.798, -117.2425]);
  assert.match(c.text, /turn left onto Mission Blvd/);
  assert.equal(c.arrived, false);
});

test('off route needs two fixes in a row; arrival near the end', () => {
  const o1 = N.status(r, [32.7990, -117.2380]);
  assert.equal(o1.offRoute, false);
  const o2 = N.status(r, [32.7990, -117.2380], o1);
  assert.equal(o2.offRoute, true);
  const end = N.status(r, [32.79705, -117.244]);
  assert.equal(end.arrived, true);
  assert.equal(end.text, 'Arrive at Crystal Pier');
});

test('distance format', () => {
  assert.equal(N.fmtDist(5), 'Now');
  assert.equal(N.fmtDist(91.44), '300 ft');
  assert.equal(N.fmtDist(1609.34), '1.0 mi');
});

// Max t451u: "it assumed I turned and gave the next direction before I did." The Garnet turn is at
// (32.798, -117.240); Garnet runs west (bearing ~270).
test('turn advance waits until you are past the turn and heading down the new road', () => {
  const before = N.status(r, [32.79807, -117.24], null, { course: 180, speed: 5 });  // ~8 m before the corner
  assert.equal(before.next.name, 'Garnet Ave', 'build 41 rule already showed Mission here');
  const corner = N.status(r, [32.798, -117.24004], null, { course: 180, speed: 5 });  // at the corner, still facing south
  assert.equal(corner.next.name, 'Garnet Ave');
  const turned = N.status(r, [32.798, -117.24008], null, { course: 268, speed: 5 });   // ~7 m onto Garnet, facing west
  assert.equal(turned.next.name, 'Mission Blvd');
  const noCourse = N.status(r, [32.798, -117.24008], null, { course: -1, speed: null });
  assert.equal(noCourse.next.name, 'Garnet Ave', 'no course: wait for 20 m');
  const far = N.status(r, [32.798, -117.24025], null, null);                           // ~23 m down Garnet
  assert.equal(far.next.name, 'Mission Blvd');
});
