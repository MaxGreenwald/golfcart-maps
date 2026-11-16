// Return-by and range nudges for a rental. Pure: the page supplies the clock,
// the legal-route miles home, and the cart's full-charge range.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMRemind = api;
})(typeof self !== 'undefined' ? self : this, function () {
  const LEAVE_LEAD_MIN = 15;
  const RANGE_MARGIN = 0.8;
  const CART_MPH = { golf_cart: 12, lsv: 18 };

  function clockMinutes(hhmm) {
    const m = /^(\d{2}):(\d{2})$/.exec(String(hhmm || '').trim());
    if (!m) return null;
    const h = +m[1], min = +m[2];
    if (h > 23 || min > 59) return null;
    return h * 60 + min;
  }

  // Minutes from now until today's HH:MM on the device clock. Negative when that time has passed.
  function minutesUntil(now, hhmm) {
    const target = clockMinutes(hhmm);
    if (target == null || !now || Number.isNaN(now.getTime())) return null;
    const cur = now.getHours() * 60 + now.getMinutes() + now.getSeconds() / 60;
    return target - cur;
  }

  function pathMiles(points, hav) {
    if (!points || points.length < 2 || typeof hav !== 'function') return null;
    let meters = 0;
    for (let i = 1; i < points.length; i++) meters += hav(points[i - 1], points[i]);
    if (!Number.isFinite(meters) || meters < 0) return null;
    return meters / 1609.344;
  }

  function travelMinutes(miles, vehicle) {
    if (!(miles >= 0)) return null;
    const mph = CART_MPH[vehicle] || CART_MPH.golf_cart;
    return miles / mph * 60;
  }

  // slack = minutes you can wait before you must leave to arrive by return_by.
  // travelMin is required (0 when the shop set a time and no return pin).
  function timeNudge(o) {
    o = o || {};
    const until = minutesUntil(o.now, o.returnBy);
    if (until == null || !Number.isFinite(+o.travelMin)) return null;
    const slack = until - Math.max(0, +o.travelMin);
    if (slack > LEAVE_LEAD_MIN) return null;
    if (slack > 0) {
      const n = Math.max(1, Math.ceil(slack));
      return { id: 'leave-window', text: n === 1 ? 'Head back in 1 minute.' : 'Head back in ' + n + ' minutes.' };
    }
    if (until > 0) return { id: 'leave-now', text: 'Head back now to make your return time.' };
    return { id: 'overdue', text: 'You are due back at the shop.' };
  }

  // Warn when the ride home is past 80% of the charge left, same margin as the map range check.
  function rangeNudge(o) {
    o = o || {};
    const range = +o.rangeMi, home = +o.homeMi;
    if (!(range > 0) || !(home >= 0) || home < 0.2) return null;
    const raw = o.batteryPct;
    const b = raw == null || raw === '' ? 100 : Math.min(100, Math.max(0, +raw));
    const eff = range * b / 100;
    if (!(eff > 0)) return { id: 'range-empty', text: 'This cart has little range left for the ride back.' };
    const ratio = home / eff;
    if (ratio > 1) return { id: 'range-short', text: 'The ride back is longer than this cart\u2019s range.' };
    if (ratio > RANGE_MARGIN) return { id: 'range-close', text: 'The ride back is close to this cart\u2019s range. Head toward the shop.' };
    return null;
  }

  function nudges(o) {
    const out = [];
    const t = timeNudge(o), r = rangeNudge(o);
    if (t) out.push(t);
    if (r) out.push(r);
    return out;
  }

  return { LEAVE_LEAD_MIN, RANGE_MARGIN, CART_MPH, clockMinutes, minutesUntil, pathMiles, travelMinutes, timeNudge, rangeNudge, nudges };
});
