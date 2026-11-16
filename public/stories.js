// Stop stories (renter experiences). After the arrival callout, the shop's note for that
// stop is spoken through the same voice path as turn-by-turn (mute + ducking stay there).
// Pure: no DOM, no speech. p.js and carplay.js decide when to say each line.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMStories = api;
})(typeof self !== 'undefined' ? self : this, function () {
  const MAX = 600;
  // About 80 m. Matches a stop address, or a parking pin a later change may route to.
  const MATCH_DEG = 0.0008;

  function storyLine(note) {
    let t = String(note == null ? '' : note);
    t = t.replace(/\s*[\u2014\u2013]\s*/g, ', ');
    t = t.replace(/[\u0000-\u001f]+/g, ' ').replace(/\s+/g, ' ').trim();
    return t.slice(0, MAX);
  }

  function callout(place) {
    const name = String(place || '').trim() || 'the stop';
    return 'You\u2019ve arrived at ' + name + '.';
  }

  // callout keeps today's sentence, including the next-stop offer. story is the note, or ''.
  function arrivalLines(place, note, nextLabel) {
    let line = callout(place);
    const next = String(nextLabel || '').trim();
    if (next) line += ' Next stop: ' + next + '.';
    return { callout: line, story: storyLine(note) };
  }

  function near(aLat, aLon, bLat, bLon) {
    return Number.isFinite(+aLat) && Number.isFinite(+aLon) && Number.isFinite(+bLat) && Number.isFinite(+bLon)
      && Math.abs(+aLat - +bLat) < MATCH_DEG && Math.abs(+aLon - +bLon) < MATCH_DEG;
  }

  // Which saved stop note goes with this arrival. dest is the spoken place name.
  // to is the coordinate navigation ended at (the address, or a parking pin).
  function matchNote(stops, to, dest) {
    const name = String(dest || '').trim().toLowerCase();
    const list = stops || [];
    if (name) {
      const byName = list.find(s => String(s.name || s.label || '').trim().toLowerCase() === name);
      if (byName) return storyLine(byName.note);
    }
    if (!to) return '';
    const byLL = list.find(s => near(s.lat, s.lon, to.lat, to.lon) || near(s.park_lat, s.park_lon, to.lat, to.lon));
    return byLL ? storyLine(byLL.note) : '';
  }

  // One spoken line per GPS fix after arrival, so CarPlay (which speaks `say` once per fix)
  // says the callout, then the note. phase: idle -> callout -> story -> done.
  function onArrive(state, o) {
    const st = state && state.phase ? state : { phase: 'idle' };
    if (!o || !o.arrived) return { state: { phase: 'idle' }, say: null };
    if (st.phase === 'idle') {
      const story = storyLine(o.story);
      return { state: { phase: story ? 'story' : 'done' }, say: o.callout || null };
    }
    if (st.phase === 'story') return { state: { phase: 'done' }, say: storyLine(o.story) || null };
    return { state: { phase: 'done' }, say: null };
  }

  return { MAX, MATCH_DEG, storyLine, callout, arrivalLines, matchNote, onArrive };
});
