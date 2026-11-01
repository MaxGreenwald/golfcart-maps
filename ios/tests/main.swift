import Foundation
// CarPlay start-view logic test (top-level code needs the file to be named main.swift)
// Run: swiftc ios/App/App/CarPlayStartView.swift ios/tests/main.swift -o /tmp/cpsv && /tmp/cpsv
var fails = 0
func ck(_ name: String, _ ok: Bool) { print((ok ? "PASS " : "FAIL ") + name); if !ok { fails += 1 } }
let json = try! Data(contentsOf: URL(fileURLWithPath: "public/data/regions.json"))
let towns = CarPlayStartView.towns(from: json)
ck("regions.json parses to towns", towns.count > 10)
let sd = towns.first { $0.id == "sd" }!
let fix = CarPlayStartView.pick(lastFix: (32.79, -117.25), savedCenter: (1, 1), phoneTown: (2, 2), towns: towns)!
ck("fix wins at driving zoom", fix.source == "last-fix" && fix.meters == 1000 && fix.lat == 32.79)
ck("saved center next", CarPlayStartView.pick(lastFix: nil, savedCenter: (1, 1), phoneTown: (2, 2), towns: towns)?.source == "saved")
ck("phone town next", CarPlayStartView.pick(lastFix: nil, savedCenter: nil, phoneTown: (2, 2), towns: towns)?.source == "phone-town")
let ft = CarPlayStartView.pick(lastFix: nil, savedCenter: nil, phoneTown: nil, towns: towns)!
ck("first town, never US default", ft.source == "first-town" && ft.meters <= 5000)
ck("nothing known gives nil (caller keeps waiting for a fix)", CarPlayStartView.pick(lastFix: nil, savedCenter: nil, phoneTown: nil, towns: []) == nil)
ck("San Diego is the first town", towns.first?.id == sd.id)
// Guidance card covering the left 40% of an 800x480 screen: dot must land in the right part, below middle.
let b = CGRect(x: 0, y: 0, width: 800, height: 480), safe = CGRect(x: 320, y: 40, width: 480, height: 440)
let f = CarPlayStartView.mapFrame(bounds: b, safe: safe)
ck("map still covers the whole screen", f.contains(b))
ck("dot (map center) is inside the uncovered area", safe.contains(CGPoint(x: f.midX, y: f.midY)) && f.midX == 560)
ck("dot sits slightly below the middle", f.midY > safe.midY && f.midY < safe.maxY)
ck("no panel: map is the screen", CarPlayStartView.mapFrame(bounds: b, safe: CGRect(x: 0, y: 0, width: 800, height: 480)).midX == 400)
// Guidance: CarPlay's safe area does not exclude the maneuver card (Max's 800-wide aftermarket unit, t415u).
for (w, h, side) in [(800.0, 480.0, 90.0), (748.0, 456.0, 90.0), (1280.0, 480.0, 90.0), (1920.0 / 3 * 2, 720.0 / 3 * 2, 90.0)] {
    let bb = CGRect(x: 0, y: 0, width: w, height: h), sf = CGRect(x: side, y: 44, width: w - side, height: h - 44)
    // Card as drawn by CarPlay: leading edge of the safe area, about 300 pt wide, top 60% of the height.
    let card = CGRect(x: sf.minX + 8, y: sf.minY + 8, width: min(330, sf.width * 0.48), height: h * 0.6)
    let dot = CarPlayStartView.dotPoint(bounds: bb, safe: sf, guiding: true)
    let mf = CarPlayStartView.mapFrame(bounds: bb, safe: sf, guiding: true)
    ck("\(Int(w))x\(Int(h)): guiding dot clear of the card", !card.insetBy(dx: -12, dy: -12).contains(dot))
    ck("\(Int(w))x\(Int(h)): guiding dot on screen, lower part", sf.contains(dot) && dot.y > sf.midY)
    ck("\(Int(w))x\(Int(h)): map centered on dot and covers screen", mf.midX == dot.x && mf.midY == dot.y && mf.contains(bb))
}
// Off-route rule matches the phone (navfollow.js: 30 m, 5 s, 10 s cooldown).
var tr = CarPlayOffRoute()
ck("on route never fires", !(0..<20).contains { tr.update(offMeters: 10, now: Double($0)) })
var fired: [Int] = []
for t in 0..<30 { if tr.update(offMeters: 80, now: 100 + Double(t)) { fired.append(t) } }
ck("off 5 s fires, then 10 s cooldown", fired == [5, 15, 25])
var tr2 = CarPlayOffRoute()
ck("one noisy fix does not fire", !tr2.update(offMeters: 80, now: 0) && !tr2.update(offMeters: 5, now: 6) && !tr2.update(offMeters: 80, now: 7))
let line = [(32.8400, -117.2600), (32.8400, -117.2500)]
ck("distance to route ~0 on it", CarPlayOffRoute.distance(from: (32.8400, -117.2550), toLine: line) < 1)
let dd = CarPlayOffRoute.distance(from: (32.8405, -117.2550), toLine: line)
ck("distance to route ~55 m off (got \(Int(dd)))", abs(dd - 55) < 3)
// Heading-up matches the phone (PR #33).
let east = [(32.84, -117.26), (32.84, -117.25)], northThenEast = [(32.84, -117.26), (32.8402, -117.26), (32.8402, -117.25)]
let rb = CarPlayHeading.routeBearing(from: (32.84, -117.255), line: east)!
ck("route bearing east ~90 (got \(Int(rb)))", abs(rb - 90) < 1)
let rb2 = CarPlayHeading.routeBearing(from: (32.84, -117.26), line: northThenEast)!
ck("looks 25 m ahead around a corner (got \(Int(rb2)))", rb2 > 0 && rb2 < 90)
ck("on route uses route bearing", CarPlayHeading.pick(current: nil, routeBearing: 90, offRouteM: 5, course: 180, speed: 5) == 90)
ck("off route uses GPS course", CarPlayHeading.pick(current: 90, routeBearing: 90, offRouteM: 80, course: 180, speed: 5) == 180)
ck("off route and stopped keeps heading (never compass)", CarPlayHeading.pick(current: 90, routeBearing: 90, offRouteM: 80, course: 180, speed: 0) == nil)
ck("ignores under 5 degrees", CarPlayHeading.pick(current: 90, routeBearing: 93, offRouteM: 5, course: nil, speed: 5) == nil)
ck("wraps 358 -> 2 as 4 degrees", CarPlayHeading.pick(current: 358, routeBearing: 2, offRouteM: 5, course: nil, speed: 5) == nil)
// CarPlay map icon
ck("icon decodes png data url", CarPlayIcon.decode("data:image/png;base64,iVBORw0KGgo=")?.count == 8)
ck("icon rejects other urls", CarPlayIcon.decode("https://x/y.png") == nil && CarPlayIcon.decode(nil) == nil && CarPlayIcon.decode("data:image/svg+xml;base64,AAAA") == nil)
ck("cart faces right heading east, map north-up", CarPlayIcon.faceSide(heading: 90, mapHeading: 0, prev: 1) == -1)
ck("cart faces left heading west", CarPlayIcon.faceSide(heading: 270, mapHeading: 0, prev: -1) == 1)
ck("heading-up (map = heading) keeps previous side", CarPlayIcon.faceSide(heading: 90, mapHeading: 90, prev: -1) == -1)
// Route trim behind the driver
let tl = [(0.0, 0.0), (0.0, 0.001), (0.0, 0.002)]
let tr = CarPlayTrim.ahead(of: (0.0001, 0.0015), line: tl)
ck("trim drops what is behind", tr.count == 2 && abs(tr[0].1 - 0.0015) < 1e-9 && tr[1].1 == 0.002)
ck("trim before the start keeps the whole line", CarPlayTrim.ahead(of: (0, -0.001), line: tl).count == 3)
// Experience tour
var tour = CarPlayTour(title: "PB", stops: [.init(name: "A", lat: 0, lon: 0), .init(name: "B", lat: 0, lon: 0)], prevMode: "golf_cart")
ck("tour starts at stop 1", tour.current?.name == "A" && !tour.isLast)
ck("tour next stop in order", tour.advance()?.name == "B" && tour.isLast)
ck("tour ends after the last stop", tour.advance() == nil)
ck("stop detail short", CarPlayTour.detail(category: "fun_fact", meters: 650, coupon: "BAR10", speed: 9) == "Fun Fact · 0.4 mi")
ck("coupon only when parked", CarPlayTour.detail(category: "", meters: nil, coupon: "BAR10", speed: 0) == "Code BAR10")
exit(fails == 0 ? 0 : 1)
