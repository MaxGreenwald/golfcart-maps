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
let trimmed = CarPlayTrim.ahead(of: (0.0001, 0.0015), line: tl)
ck("trim drops what is behind", trimmed.count == 2 && abs(trimmed[0].1 - 0.0015) < 1e-9 && trimmed[1].1 == 0.002)
ck("trim before the start keeps the whole line", CarPlayTrim.ahead(of: (0, -0.001), line: tl).count == 3)
// Experience tour
var tour = CarPlayTour(title: "PB", stops: [.init(name: "A", lat: 0, lon: 0), .init(name: "B", lat: 0, lon: 0)], prevMode: "golf_cart")
ck("tour starts at stop 1", tour.current?.name == "A" && !tour.isLast)
ck("tour next stop in order", tour.advance()?.name == "B" && tour.isLast)
ck("tour ends after the last stop", tour.advance() == nil)
ck("stop detail short", CarPlayTour.detail(category: "fun_fact", meters: 650, coupon: "BAR10", speed: 9) == "Fun Fact · 0.4 mi")
ck("coupon only when parked", CarPlayTour.detail(category: "", meters: nil, coupon: "BAR10", speed: 0) == "Code BAR10")
// t451u: build 41's reroute heading. Replay of the failure: driving west (270) at 6 m/s, then slowing to 1.2 m/s
// with iOS reporting course -1 when the 5 s off-route timer fires. Old rule (speed >= 1.5 && course >= 0) gave no heading.
func oldRerouteHeading(course: Double, speed: Double) -> Double? { (speed >= 1.5 && course >= 0) ? course : nil }
var cc = CarPlayCourse()
var lon0 = -117.2470
for i in 0..<6 { cc.update(lat: 32.7973, lon: lon0, course: 270, speed: 6, accuracy: 5, now: Double(i)); lon0 -= 6 / (cos(32.7973 * .pi / 180) * 111_320) }
cc.update(lat: 32.7973, lon: lon0, course: -1, speed: 1.2, accuracy: 5, now: 7)
ck("replay: old rule drops the heading when slowing (bug)", oldRerouteHeading(course: -1, speed: 1.2) == nil)
ck("replay: new rule keeps the last course from the past 10 s", cc.forReroute(now: 7).map { abs($0 - 270) < 1 } == true)
ck("course goes stale after 10 s", cc.forReroute(now: 17) == nil)
var cs = CarPlayCourse(); cs.update(lat: 32.79, lon: -117.25, course: 90, speed: 5, accuracy: 5, now: 0); cs.update(lat: 32.79, lon: -117.25, course: -1, speed: 0, accuracy: 5, now: 2)
ck("stopped: no heading (any direction is fine)", cs.forReroute(now: 2) == nil)
var cm = CarPlayCourse()
cm.update(lat: 32.79, lon: -117.25, course: -1, speed: -1, accuracy: 5, now: 0)
cm.update(lat: 32.7901, lon: -117.25, course: -1, speed: -1, accuracy: 5, now: 3)
ck("course from movement when iOS gives -1 (got \(cm.forReroute(now: 3) ?? -1))", cm.forReroute(now: 3).map { $0 < 2 || $0 > 358 } == true)
// Wrong way while still on the route line: never counted as off route in build 41.
var ww = CarPlayWrongWay()
let wfired = (0..<7).map { ww.update(course: 270, speed: 5, routeBearing: 90, onRoute: true, now: Double($0)) }
ck("wrong way on the line fires after 5 s", wfired == [false, false, false, false, false, true, false])
var ww2 = CarPlayWrongWay()
ck("right way never fires", !(0..<20).contains { ww2.update(course: 95, speed: 5, routeBearing: 90, onRoute: true, now: Double($0)) })
ck("wrong way but stopped does not fire", !(0..<20).contains { ww2.update(course: 270, speed: 0.5, routeBearing: 90, onRoute: true, now: Double($0)) })
// Turn advance (t451u): a right turn north->east at (32.80,-117.25), outgoing bearing 90.
let tl0 = 32.80, tn0 = -117.25, mlon = 1 / (cos(32.80 * .pi / 180) * 111_320), mlat = 1 / 110_540.0
func adv(_ dn: Double, _ de: Double, _ c: Double?, _ v: Double = 5) -> Bool {
    CarPlayAdvance.done(lat: tl0 + dn * mlat, lon: tn0 + de * mlon, course: c, speed: v, turnLat: tl0, turnLon: tn0, outBrg: 90, arrive: false)
}
ck("build 41 bug: 20 m before the turn no longer advances", !adv(-20, 0, 0))
ck("at the corner, still heading north: wait", !adv(0, 2, 0))
ck("5+ m into the new road, heading east: advance", adv(0, 7, 85))
ck("into the new road but heading still north (cutting the corner): wait", !adv(-3, 7, 10))
ck("20 m down the new road: advance even without a course", adv(0, 21, nil))
ck("went straight past the turn: never advances (off-route handles it)", !adv(40, 0, 0) && !adv(25, 3, 0))
ck("arrival keeps the 25 m radius", CarPlayAdvance.done(lat: tl0 + 20 * mlat, lon: tn0, course: nil, speed: 0, turnLat: tl0, turnLon: tn0, outBrg: nil, arrive: true))
// Arrive text
ck("arrive names the place", CarPlayArrive.text(name: "Destiny Coast", address: "1 Beach Rd") == "Arrive at Destiny Coast")
ck("arrive falls back to address", CarPlayArrive.text(name: "Place", address: "1 Beach Rd") == "Arrive at 1 Beach Rd")
ck("arrive last resort", CarPlayArrive.text(name: nil, address: nil) == "Arrive at destination")
// Celebration banner centered in the safe area and fully inside it at Apple's test sizes.
for (w, h) in [(800.0, 480.0), (1920.0 / 3 * 2, 720.0 / 3 * 2), (748.0, 456.0), (1280.0, 480.0)] {
    let bb = CGRect(x: 0, y: 0, width: w, height: h), sf = CGRect(x: 0, y: 44, width: w, height: h - 44)
    let bf = CarPlayCelebrate.bannerFrame(bounds: bb, safe: sf)
    ck("\(Int(w))x\(Int(h)): banner inside safe area, below the nav bar", sf.contains(bf) && bf.minY > 44)
    ck("\(Int(w))x\(Int(h)): banner centered", abs(bf.midX - sf.midX) <= 1 && abs(bf.midY - sf.midY) <= 1)
    // Conservative width estimate: 0.62 em per char, emoji counted as 2 chars.
    let est: (String, CGFloat) -> CGFloat = { t, sz in CGFloat(t.unicodeScalars.reduce(0) { $0 + ($1.value > 0xFFFF ? 2 : 1) }) * sz * 0.62 }
    let fs = CarPlayCelebrate.fontSizes(banner: bf, measure: est), inner = bf.width - 2 * CarPlayCelebrate.padX
    ck("\(Int(w))x\(Int(h)): both banner lines fit the width (t454u)", est(CarPlayCelebrate.line1, fs.title) <= inner && est(CarPlayCelebrate.line2, fs.sub) <= inner && fs.title >= 14)
    ck("\(Int(w))x\(Int(h)): two lines fit the height", (fs.title + fs.sub) * 1.22 <= bf.height - 2 * CarPlayCelebrate.padY)
    ck("\(Int(w))x\(Int(h)): unicorn lanes inside safe area", CarPlayCelebrate.lanes(count: 8, safe: sf).allSatisfy { $0.y >= sf.minY && $0.y + $0.size <= sf.maxY })
}
ck("banner text (t454u)", CarPlayCelebrate.line1 == "You have Arrived!" && CarPlayCelebrate.line2 == "Have a wonderful life you LEGEND 🦄")
ck("celebration lasts 15 s", CarPlayCelebrate.seconds == 15)
// Search rows
ck("long title clipped", CarPlaySearchText.clip("Pacific Beach Boardwalk Shops and Restaurants", 28)!.count == 28)
ck("address drops ZIP and country", CarPlaySearchText.shortAddress("123 Main St, San Diego, CA 92109, United States") == "123 Main St, San Diego")
ck("prefix matches first, then nearest", CarPlaySearchText.rank([("The Crystal Pier", 100), ("Crystal Pier Hotel", 900), ("Crystal Cove", 50)], query: "crys") == [2, 1, 0])
exit(fails == 0 ? 0 : 1)
