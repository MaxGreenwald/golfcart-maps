// Where navigation ends for an experience stop. A parking pin within PARK_MAX_M
// of the address wins. Farther pins are ignored. Keep in step with lib/partner.js parkPoint.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMPark = api;
})(typeof self !== 'undefined' ? self : this, function () {
  const PARK_MAX_M = 800;
  function meters(aLat, aLon, bLat, bLon) {
    const R = 6371000, rad = Math.PI / 180;
    const dLat = (bLat - aLat) * rad, dLon = (bLon - aLon) * rad;
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(aLat * rad) * Math.cos(bLat * rad) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(x)));
  }
  function parkPoint(stop) {
    if (!stop) return null;
    const lat = +stop.lat, lon = +stop.lon, plat = +stop.park_lat, plon = +stop.park_lon;
    if (![lat, lon, plat, plon].every(Number.isFinite)) return null;
    if (Math.abs(plat) > 90 || Math.abs(plon) > 180) return null;
    if (meters(lat, lon, plat, plon) > PARK_MAX_M) return null;
    return { lat: plat, lon: plon };
  }
  // The point the route should end at. parked is false when we use the address.
  function dest(stop) {
    const p = parkPoint(stop);
    const lat = p ? p.lat : +stop.lat, lon = p ? p.lon : +stop.lon;
    return { lat, lon, parked: !!p };
  }
  return { PARK_MAX_M, parkPoint, dest, meters };
});
