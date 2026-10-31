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
exit(fails == 0 ? 0 : 1)
