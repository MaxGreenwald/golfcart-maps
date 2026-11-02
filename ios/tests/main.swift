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
// Off-route, heading-up, reroute course, wrong way and turn advance moved to the shared phone engine (t459u,
// AGENTS.md rule 35): tests/nav_shared.test.mjs, tests/navfollow.test.mjs and tests/nav.test.mjs cover them for both paths.
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
    ck("\(Int(w))x\(Int(h)): unicorn lanes inside safe area", CarPlayCelebrate.lanes(count: 8, safe: sf).allSatisfy { $0.y >= sf.minY && $0.y + $0.size <= sf.maxY })
}
ck("celebration lasts 15 s", CarPlayCelebrate.seconds == 15)
// Search rows
ck("long title clipped", CarPlaySearchText.clip("Pacific Beach Boardwalk Shops and Restaurants", 28)!.count == 28)
ck("address drops ZIP and country", CarPlaySearchText.shortAddress("123 Main St, San Diego, CA 92109, United States") == "123 Main St, San Diego")
ck("prefix matches first, then nearest", CarPlaySearchText.rank([("The Crystal Pier", 100), ("Crystal Pier Hotel", 900), ("Crystal Cove", 50)], query: "crys") == [2, 1, 0])
// Follow camera (t456u-t458u): zoom persists, pan pauses, idle resumes.
var fc = CarPlayFollow(); fc.resume()
ck("default zoom when driver never zoomed", fc.distance(default: 720) == 720)
let zin = fc.zoom(current: 720, factor: 0.5)
ck("+ halves distance and is remembered", zin == 360 && fc.distance(default: 720) == 360)
ck("zoom keeps following", fc.following)
ck("zoom clamps", fc.zoom(current: 200, factor: 0.5) == CarPlayFollow.minM && fc.zoom(current: 50_000, factor: 2) == CarPlayFollow.maxM)
fc.pan(now: 1000)
ck("pan pauses follow", !fc.following)
ck("no resume before idle", !fc.shouldAutoResume(now: 1000 + CarPlayFollow.idleResume - 1))
ck("resume after idle", fc.shouldAutoResume(now: 1000 + CarPlayFollow.idleResume) && fc.following)
ck("resume fires once", !fc.shouldAutoResume(now: 2000))
ck("zoom survives pan + resume", fc.distance(default: 720) == CarPlayFollow.maxM)
// Voice (t455u): mute setting. Turn-timing now comes from the shared phone engine (carplay.js navFix say, t459u).
let vd = UserDefaults(suiteName: "gcm-voice-test")!; vd.removeObject(forKey: GCMVoiceSetting.key)
ck("voice is on by default", !GCMVoiceSetting.isMuted(vd))
GCMVoiceSetting.setMuted(true, vd); ck("mute is saved", GCMVoiceSetting.isMuted(vd))
// Reroute telemetry ring (t453u): last 200 lines, PT time stamps.
var lg = CarPlayNavLog(); for i in 0..<250 { lg.add("x\(i)") }
ck("nav log keeps the last 200 lines", lg.lines.count == 200 && lg.lines.last!.hasSuffix("x249"))
exit(fails == 0 ? 0 : 1)
