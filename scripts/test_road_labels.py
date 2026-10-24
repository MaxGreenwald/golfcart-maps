"""Road popups must match the road-rule module (public/roadrule.js via GCMRule on the page).

Samples Avoid and OK segments in San Diego (golf cart mode), opens each popup by
finding the Leaflet layer for that exact segment (same approach as test_safety_caution),
and checks the status line.

A road wrongly shown as legal is the worst failure: if GCMRule.cls === 3 the popup must say
Avoid and must not say "OK for".

Usage: URL=https://golfcartmap.com/map/ python3 scripts/test_road_labels.py
"""
from playwright.sync_api import sync_playwright
import os, sys

URL = os.environ.get("URL", "http://localhost:8765/map/")
fails = []


def ck(n, c, x=""):
    print(("PASS " if c else "FAIL ") + n, (x[:220] if isinstance(x, str) else x))
    if not c:
        fails.append(n)


# Return segment fingerprints (name, mph, src, cls, endpoints) — enough to re-find the layer.
SAMPLE = """
async () => {
  await ensure(32.78, -117.29, 32.86, -117.24);
  const out = {avoid: [], ok: []};
  for (const s of D.segs) {
    if (!s || !s[7] || s[7].length < 2) continue;
    if (s[3] === 'c') continue;
    const c = GCMRule.cls(s, RULE);
    const name = D.names[s[0]] || '';
    if (!name) continue;
    const q0 = s[7][0], q1 = s[7][s[7].length - 1];
    const row = {name, mph: s[2], src: s[3], cls: c, q0, q1, flag: s[9] || 0};
    if (c === 3 && out.avoid.length < 6) out.avoid.push(row);
    if (c !== 3 && s[2] != null && s[2] <= RULE.max_posted && out.ok.length < 4) out.ok.push(row);
    if (out.avoid.length >= 6 && out.ok.length >= 4) break;
  }
  return out;
}
"""

# Find the polyline whose endpoints match the segment, click it, return popup + draw color + _rseg.
POP = """
(async (name, mph, src, q0, q1) => {
  await ensure(Math.min(q0[1], q1[1]) - 0.01, Math.min(q0[0], q1[0]) - 0.01,
               Math.max(q0[1], q1[1]) + 0.01, Math.max(q0[0], q1[0]) + 0.01);
  let seg = null, bd = 1;
  for (const x of D.segs) {
    if (!x || D.names[x[0]] !== name || Number(x[2]) !== Number(mph) || x[3] !== src) continue;
    const a = x[7][0], z = x[7][x[7].length - 1];
    const d = Math.abs(a[0] - q0[0]) + Math.abs(a[1] - q0[1]) + Math.abs(z[0] - q1[0]) + Math.abs(z[1] - q1[1]);
    if (d < bd) { bd = d; seg = x; }
  }
  if (!seg || bd > 1e-5) return {err: 'NO SEG ' + bd};
  const q = seg[7][0];
  map.closePopup();
  map.setView([q[1], q[0]], 18);
  await new Promise(r => setTimeout(r, 1200));
  let pl = null;
  const z = seg[7][seg[7].length - 1];
  layer.eachLayer(g => {
    (g.eachLayer ? g : {eachLayer: f => f(g)}).eachLayer(l => {
      const A = l.getLatLngs && l.getLatLngs();
      if (!A || A.length < 2) return;
      const ll = A[0], lz = A[A.length - 1];
      if (ll && Math.abs(ll.lat - q[1]) < 1e-6 && Math.abs(ll.lng - q[0]) < 1e-6
          && Math.abs(lz.lat - z[1]) < 1e-6 && Math.abs(lz.lng - z[0]) < 1e-6) pl = l;
    });
  });
  if (!pl) return {err: 'NO LINE'};
  pl.fire('click', {latlng: L.latLng(q[1], q[0])});
  await new Promise(r => setTimeout(r, 250));
  const txt = (document.querySelector('.leaflet-popup-content') || {}).innerText || '';
  const color = (pl.options && pl.options.color) || '';
  const status = (window._rseg && window._rseg.status) || '';
  const road = (window._rseg && window._rseg.road) || '';
  return {txt, color, status, road, moduleCls: GCMRule.cls(seg, RULE)};
})"""


def pop_row(pg, row):
    return pg.evaluate(
        POP + f"({row['name']!r},{row['mph']!r},{row['src']!r},{row['q0']},{row['q1']})"
    )


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1200, "height": 900})
    pg.on("pageerror", lambda e: fails.append("js " + str(e)[:120]))
    # Force golf cart mode via query (stricter CA cap → more Avoid samples)
    join = "&" if "?" in URL else "?"
    dest = URL if "veh=" in URL else (URL.rstrip("/") + join + "r=sd&veh=golf_cart")
    pg.goto(dest)
    pg.wait_for_function("window.ready===true && window.GCMRule && window.REG", timeout=120000)
    pg.wait_for_timeout(500)
    ck("golf cart mode for label check", pg.evaluate("MODE") == "golf_cart", pg.evaluate("MODE"))
    ck("San Diego region", pg.evaluate("REG.id") == "sd", pg.evaluate("REG.id"))
    sample = pg.evaluate(SAMPLE)
    ck("sampled Avoid segments", len(sample.get("avoid") or []) >= 3, repr({k: len(sample.get(k) or []) for k in ("avoid", "ok")}))
    ck("sampled OK segments", len(sample.get("ok") or []) >= 2, repr({k: len(sample.get(k) or []) for k in ("avoid", "ok")}))

    for row in sample.get("avoid") or []:
        v = pop_row(pg, row)
        if not isinstance(v, dict) or v.get("err"):
            ck(f"Avoid popup opens: {row['name']} {row['mph']}mph", False, repr(v)[:200])
            continue
        txt, status, color, road = v.get("txt") or "", v.get("status") or "", v.get("color") or "", v.get("road") or ""
        # Confirm we hit the intended road (name match) before judging legal/avoid
        if road and road != row["name"] and row["name"] not in txt.split("\n")[0]:
            ck(f"Avoid popup correct road: {row['name']}", False, f"got road={road!r} txt0={(txt.split(chr(10)) or [''])[0]!r}")
            continue
        shown_ok = status.startswith("OK for") or (
            "OK for" in txt and "Avoid" not in txt and color == "#12a150"
        )
        shown_avoid = status == "Avoid" or "Avoid" in txt or color == "#e5484d"
        # Safety-caution Avoid roads are dashed orange (#f08c00) but status must still be Avoid
        ck(
            f"Avoid label: {row['name']} {row['mph']}mph",
            (shown_avoid and not shown_ok) or (color == "#f08c00" and "Avoid" in (status + txt) and not status.startswith("OK for")),
            f"status={status!r} color={color} moduleCls={v.get('moduleCls')} txt={txt[:140]!r}",
        )
        if shown_ok:
            ck(
                f"wrongly legal: {row['name']}",
                False,
                f"GCMRule.cls=3 but UI shows legal. status={status!r} color={color} txt={txt[:140]!r}",
            )

    for row in sample.get("ok") or []:
        v = pop_row(pg, row)
        if not isinstance(v, dict) or v.get("err"):
            ck(f"OK popup opens: {row['name']} {row['mph']}mph", False, repr(v)[:200])
            continue
        txt, status = v.get("txt") or "", v.get("status") or ""
        ck(
            f"OK label: {row['name']} {row['mph']}mph",
            ("OK for" in txt or status.startswith("OK for")) and "Avoid:" not in txt,
            f"status={status!r} txt={txt[:140]!r}",
        )

    r = pg.evaluate("testRoute([32.8506,-117.2717],[32.8305,-117.2805]).then(r=>r&&r.mi)")
    ck("SD route search returns a legal route", bool(r), r)
    b.close()

print("RESULT", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
sys.exit(1 if fails else 0)
