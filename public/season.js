// Seasonal experiences: a shop can give a ride a "show from" and "show until" date (YYYY-MM-DD,
// either optional). Shared by the partner Worker, the renter page, CarPlay and the admin.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMSeason = api;
})(typeof self !== 'undefined' ? self : this, function () {
  const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;
  const MAX_SPAN_DAYS = 366;
  function validDay(s) {
    const m = DAY.exec(String(s || ''));
    if (!m) return false;
    const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3];
  }
  /** { skip } | { starts_on, ends_on } | { error }. Empty strings clear a date. */
  function clean(body) {
    const b = body || {};
    if (b.starts_on === undefined && b.ends_on === undefined) return { skip: true };
    const s = String(b.starts_on || '').trim(), e = String(b.ends_on || '').trim();
    if (s && !validDay(s)) return { error: 'Show from must be a date' };
    if (e && !validDay(e)) return { error: 'Show until must be a date' };
    if (s && e && e < s) return { error: 'Show until is before show from' };
    if (s && e && (Date.parse(e) - Date.parse(s)) / 864e5 > MAX_SPAN_DAYS) return { error: 'A season can be up to a year long' };
    return { starts_on: s, ends_on: e };
  }
  function localDay(d) {
    const p = n => String(n).padStart(2, '0');
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }
  /** On the device: today's local date is inside the window (both ends included). */
  function inSeason(ex, now) {
    const t = localDay(now || new Date());
    const s = ex && ex.starts_on, e = ex && ex.ends_on;
    return !(s && t < s) && !(e && t > e);
  }
  /** On the Worker (UTC clock): keep anything in season somewhere in US time zones today. */
  function maybeInSeason(ex, nowMs) {
    const early = new Date(nowMs + 14 * 3600e3).toISOString().slice(0, 10);
    const late = new Date(nowMs - 14 * 3600e3).toISOString().slice(0, 10);
    const s = ex && ex.starts_on, e = ex && ex.ends_on;
    return !(s && early < s) && !(e && late > e);
  }
  const MONTHS = { en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    es: ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'] };
  function fmt(day, lang) {
    if (!validDay(day)) return '';
    const [, , m, d] = DAY.exec(day);
    const mo = (MONTHS[lang] || MONTHS.en)[+m - 1];
    return lang === 'es' ? (+d) + ' ' + mo : mo + ' ' + (+d);
  }
  /** "Dec 1 to Jan 2", "From Dec 1", "Until Jan 2", or "" (always on). */
  function label(ex, lang) {
    const s = ex && ex.starts_on, e = ex && ex.ends_on;
    const es = lang === 'es';
    if (s && e) return fmt(s, lang) + (es ? ' al ' : ' to ') + fmt(e, lang);
    if (s) return (es ? 'Desde el ' : 'From ') + fmt(s, lang);
    if (e) return (es ? 'Hasta el ' : 'Until ') + fmt(e, lang);
    return '';
  }
  return { clean, inSeason, maybeInSeason, label, validDay, localDay };
});
