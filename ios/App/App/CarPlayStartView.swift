import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

/// Picks where the CarPlay map opens. Pure logic (Foundation only) so CI can test it without a device.
/// Order: fresh GPS fix > last known fix > last CarPlay center > town the phone last used > first supported town. Never the zoomed-out US default.
enum CarPlayStartView {
    /// Driving zoom: about 1 km across.
    static let drivingMeters = 1000.0
    /// Town fallback zoom when we have no fix at all.
    static let townMeters = 4000.0

    struct Town { let id: String; let lat: Double; let lon: Double }
    struct Pick: Equatable { let lat: Double; let lon: Double; let meters: Double; let source: String }

    static func pick(lastFix: (Double, Double)?, savedCenter: (Double, Double)?, phoneTown: (Double, Double)?, towns: [Town]) -> Pick? {
        if let f = lastFix { return Pick(lat: f.0, lon: f.1, meters: drivingMeters, source: "last-fix") }
        if let s = savedCenter { return Pick(lat: s.0, lon: s.1, meters: drivingMeters, source: "saved") }
        if let t = phoneTown { return Pick(lat: t.0, lon: t.1, meters: townMeters, source: "phone-town") }
        if let t = towns.first { return Pick(lat: t.lat, lon: t.lon, meters: townMeters, source: "first-town") }
        return nil
    }

    /// Parses public/data/regions.json ([{id, center:[lat,lon]}, ...]).
    static func towns(from data: Data) -> [Town] {
        guard let a = (try? JSONSerialization.jsonObject(with: data)) as? [[String: Any]] else { return [] }
        return a.compactMap { r in
            guard let id = r["id"] as? String, let c = r["center"] as? [Double], c.count == 2 else { return nil }
            return Town(id: id, lat: c[0], lon: c[1])
        }
    }

    /// Where follow mode should draw the location dot. CarPlay's safe area only excludes the nav bar and
    /// sidebar, NOT the maneuver card, which sits on the leading side during guidance. So while guiding we
    /// drop the leading `cardShare` of the safe width (unless CarPlay already shrank the safe area past the
    /// card) and put the dot in the lower middle of what is left, so the road ahead shows above it.
    static let cardShare = 0.5
    static func dotPoint(bounds b: CGRect, safe: CGRect, guiding: Bool) -> CGPoint {
        guard guiding else { return CGPoint(x: safe.midX, y: min(safe.maxY, safe.midY + safe.height * 0.1)) }
        var free = safe
        let alreadyExcluded = (safe.minX - b.minX) > b.width * 0.35
        if !alreadyExcluded {
            let cut = safe.width * cardShare
            free = CGRect(x: safe.minX + cut, y: safe.minY, width: safe.width - cut, height: safe.height)
        }
        return CGPoint(x: free.midX, y: free.minY + free.height * 0.72)
    }

    /// Map frame that fills `bounds` and is centered on `dot` (MapKit follow mode draws the dot at the map
    /// view's center), so the dot lands where we want while the map still covers the whole screen.
    static func mapFrame(bounds b: CGRect, dot: CGPoint) -> CGRect {
        let hw = max(dot.x - b.minX, b.maxX - dot.x), hh = max(dot.y - b.minY, b.maxY - dot.y)
        return CGRect(x: dot.x - hw, y: dot.y - hh, width: hw * 2, height: hh * 2)
    }
    static func mapFrame(bounds b: CGRect, safe: CGRect, guiding: Bool = false) -> CGRect {
        mapFrame(bounds: b, dot: dotPoint(bounds: b, safe: safe, guiding: guiding))
    }
}

/// Off-route rule shared with the phone (public/navfollow.js offTracker): farther than 30 m from the route
/// for 5 s straight triggers one reroute, then at most one reroute per 10 s.
struct CarPlayOffRoute {
    static let offM = 30.0, offS = 5.0, cooldownS = 10.0
    private var since: Double? = nil, last = -Double.infinity
    mutating func update(offMeters: Double, now: Double) -> Bool {
        guard offMeters > Self.offM else { since = nil; return false }
        if since == nil { since = now }
        if now - since! >= Self.offS && now - last >= Self.cooldownS { last = now; since = nil; return true }
        return false
    }
    mutating func reset() { since = nil }

    /// Meters from p to the nearest point on the polyline (local flat projection, fine at street scale).
    static func distance(from p: (Double, Double), toLine line: [(Double, Double)]) -> Double {
        guard let first = line.first else { return .infinity }
        let k = cos(p.0 * .pi / 180) * 111_320.0, ky = 110_540.0
        func xy(_ q: (Double, Double)) -> (Double, Double) { ((q.1 - p.1) * k, (q.0 - p.0) * ky) }
        if line.count == 1 { let a = xy(first); return (a.0 * a.0 + a.1 * a.1).squareRoot() }
        var best = Double.infinity
        for i in 1..<line.count {
            let a = xy(line[i - 1]), b = xy(line[i])
            let dx = b.0 - a.0, dy = b.1 - a.1, L = dx * dx + dy * dy
            let t = L == 0 ? 0 : max(0, min(1, -(a.0 * dx + a.1 * dy) / L))
            let x = a.0 + t * dx, y = a.1 + t * dy
            best = min(best, (x * x + y * y).squareRoot())
        }
        return best
    }
}

/// Heading-up rule shared with the phone (PR #33): route bearing about 25 m ahead of where you are on the
/// route; GPS course when off route; never the compass; ignore changes under 5 degrees.
enum CarPlayHeading {
    static let aheadM = 25.0, minChange = 5.0

    /// Bearing (degrees) from the point on the line nearest p to the point `aheadM` further along it.
    static func routeBearing(from p: (Double, Double), line: [(Double, Double)], aheadM: Double = aheadM) -> Double? {
        guard line.count >= 2 else { return nil }
        let k = cos(p.0 * .pi / 180) * 111_320.0, ky = 110_540.0
        func xy(_ q: (Double, Double)) -> (Double, Double) { ((q.1 - p.1) * k, (q.0 - p.0) * ky) }
        var best = Double.infinity, seg = 0, pt = (0.0, 0.0)
        for i in 1..<line.count {
            let a = xy(line[i - 1]), b = xy(line[i]), dx = b.0 - a.0, dy = b.1 - a.1, L = dx * dx + dy * dy
            let t = L == 0 ? 0 : max(0, min(1, -(a.0 * dx + a.1 * dy) / L))
            let x = a.0 + t * dx, y = a.1 + t * dy, d = x * x + y * y
            if d < best { best = d; seg = i; pt = (x, y) }
        }
        var left = aheadM, cur = pt, i = seg
        while i < line.count {
            let b = xy(line[i]), dx = b.0 - cur.0, dy = b.1 - cur.1, L = (dx * dx + dy * dy).squareRoot()
            if L >= left || i == line.count - 1 {
                let f = L == 0 ? 0 : min(1, left / L)
                let tx = cur.0 + dx * f, ty = cur.1 + dy * f
                let ex = tx - pt.0, ey = ty - pt.1
                if ex == 0 && ey == 0 { return nil }
                return (atan2(ex, ey) * 180 / .pi + 360).truncatingRemainder(dividingBy: 360)
            }
            left -= L; cur = b; i += 1
        }
        return nil
    }

    /// New camera heading, or nil to keep the current one.
    static func pick(current: Double?, routeBearing: Double?, offRouteM: Double, course: Double?, speed: Double?) -> Double? {
        let onRoute = offRouteM <= CarPlayOffRoute.offM
        let moving = (speed ?? 0) >= 1
        let want: Double? = onRoute ? routeBearing : ((course ?? -1) >= 0 && moving ? course : nil)
        guard let w = want else { return nil }
        guard let c = current else { return w }
        let d = abs((w - c + 540).truncatingRemainder(dividingBy: 360) - 180)
        return d < minChange ? nil : w
    }
}

/// Map icon during CarPlay guidance, same as the phone (public/navfollow.js): cart E by default, or the user's
/// photo from Settings > Your map icon (web localStorage 'gcm_map_icon', a small round data URL).
enum CarPlayIcon {
    static let key = "gcm_map_icon"
    /// Image bytes from a data URL the phone accepts (png, jpeg, webp base64), else nil.
    static func decode(_ url: String?) -> Data? {
        guard let u = url, let r = u.range(of: "^data:image/(png|jpeg|webp);base64,", options: .regularExpression) else { return nil }
        return Data(base64Encoded: String(u[r.upperBound...]), options: .ignoreUnknownCharacters)
    }
    /// scaleX for the left-facing cart, same as navfollow.js faceSide: -1 (face right) when the on-screen
    /// direction (heading minus map heading) points right, 1 when left, keep the previous side near up/down.
    static func faceSide(heading: Double, mapHeading: Double, prev: Double) -> Double {
        let sx = sin((heading - mapHeading) * .pi / 180)
        return sx > 0.17 ? -1 : sx < -0.17 ? 1 : (prev == 0 ? 1 : prev)
    }
}

/// Route line trimmed behind the driver (t446u): snap to the nearest segment, keep the snapped point and
/// everything ahead. Points are (lat, lon).
enum CarPlayTrim {
    static func ahead(of p: (Double, Double), line: [(Double, Double)]) -> [(Double, Double)] {
        guard line.count >= 2 else { return line }
        let k = cos(p.0 * .pi / 180)
        var best = Double.infinity, bi = 0, bs = p
        for i in 0..<(line.count - 1) {
            let a = line[i], b = line[i + 1]
            let ax = (a.1 - p.1) * k, ay = a.0 - p.0, bx = (b.1 - p.1) * k, by = b.0 - p.0
            let dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy
            let t = l2 > 0 ? max(0, min(1, -(ax * dx + ay * dy) / l2)) : 0
            let x = ax + t * dx, y = ay + t * dy, d = x * x + y * y
            if d < best { best = d; bi = i; bs = (a.0 + t * (b.0 - a.0), a.1 + t * (b.1 - a.1)) }
        }
        return [bs] + line[(bi + 1)...]
    }
}

/// A partner experience driven stop by stop in order (t437s2290).
struct CarPlayTour {
    struct Stop { let name: String; let lat: Double; let lon: Double }
    let title: String, stops: [Stop], prevMode: String?
    var index = 0
    var current: Stop? { index < stops.count ? stops[index] : nil }
    /// After arriving at the current stop: the next one, or nil when the tour is done.
    mutating func advance() -> Stop? { index += 1; return current }
    var isLast: Bool { index >= stops.count - 1 }
    /// CarPlay list detail: short, e.g. "Views · 0.4 mi". Coupon only when parked (speed < 1 m/s).
    static func detail(category: String, meters: Double?, coupon: String, speed: Double) -> String {
        var parts: [String] = []
        if !category.isEmpty { parts.append(category.replacingOccurrences(of: "_", with: " ").capitalized) }
        if let m = meters { parts.append(m < 160 ? "\(Int((m * 3.28084 / 50).rounded() * 50)) ft" : String(format: "%.1f mi", m / 1609.34)) }
        if !coupon.isEmpty, speed >= 0, speed < 1 { parts.append("Code \(coupon)") }
        return parts.joined(separator: " · ")
    }
}

/// Course a reroute should honor (Max t451u). Build 41 read CLLocation.course only at the instant the 5 s
/// off-route timer fired and dropped it under 1.5 m/s or when iOS reported -1, so a driver who slowed while
/// realizing the mistake got a plan in any direction (usually "turn around"). Same rule as the phone
/// (navfollow.js travelCourse): the last good course from the past 10 s, from GPS or from our own movement.
struct CarPlayCourse {
    static let movingMS = 1.5, freshS = 10.0, stepM = 8.0, stoppedMS = 0.3
    private(set) var course: Double? = nil
    private var at = -Double.infinity
    private var anchor: (lat: Double, lon: Double, t: Double)? = nil
    private var speed = -1.0
    mutating func update(lat: Double, lon: Double, course c: Double, speed v: Double, accuracy: Double, now: Double) {
        speed = v
        if c >= 0, v >= Self.movingMS { course = c; at = now; anchor = (lat, lon, now); return }
        guard accuracy >= 0, accuracy <= 30 else { return }
        guard let a = anchor, now - a.t <= Self.freshS else { anchor = (lat, lon, now); return }
        let d = CarPlayGeo.meters(a.lat, a.lon, lat, lon)
        if d >= max(Self.stepM, accuracy) { course = CarPlayGeo.bearing(a.lat, a.lon, lat, lon); at = now; anchor = (lat, lon, now) }
    }
    /// nil when there is no course from the past 10 s, or GPS says we are stopped (then any direction is fine).
    func forReroute(now: Double) -> Double? {
        guard let c = course, now - at <= Self.freshS else { return nil }
        if speed >= 0, speed < Self.stoppedMS { return nil }
        return c
    }
}

enum CarPlayGeo {
    static func meters(_ a: Double, _ b: Double, _ c: Double, _ d: Double) -> Double {
        let k = cos((a + c) / 2 * .pi / 180) * 111_320.0
        let x = (d - b) * k, y = (c - a) * 110_540.0
        return (x * x + y * y).squareRoot()
    }
    static func bearing(_ a: Double, _ b: Double, _ c: Double, _ d: Double) -> Double {
        let x = (d - b) * cos((a + c) / 2 * .pi / 180), y = c - a
        return (atan2(x, y) * 180 / .pi + 360).truncatingRemainder(dividingBy: 360)
    }
    static func diff(_ a: Double, _ b: Double) -> Double { abs((a - b + 540).truncatingRemainder(dividingBy: 360) - 180) }
}

/// Driving against the route while still on its line never counted as off route in build 41 (the line is under
/// you), so no reroute. Course more than 120 degrees from the route bearing, moving, for 5 s straight -> reroute.
struct CarPlayWrongWay {
    static let minDiff = 120.0, holdS = 5.0
    private var since: Double? = nil
    mutating func update(course: Double?, speed: Double, routeBearing: Double?, onRoute: Bool, now: Double) -> Bool {
        guard onRoute, let c = course, let r = routeBearing, speed >= CarPlayCourse.movingMS, CarPlayGeo.diff(c, r) > Self.minDiff else { since = nil; return false }
        if since == nil { since = now }
        if now - since! >= Self.holdS { since = nil; return true }
        return false
    }
    mutating func reset() { since = nil }
}

/// When to move the card past a maneuver (Max t451u: "it assumed I turned before I did"). Build 41 advanced
/// within 25 m of the turn point, i.e. before the turn. Now: past the turn point on the outgoing road, and
/// either heading along it (within 35 degrees) or 20 m down it. Arrival keeps the 25 m radius.
enum CarPlayAdvance {
    static let pastM = 5.0, sureM = 20.0, crossM = 20.0, headingDeg = 35.0, arriveM = 25.0, nearM = 120.0
    /// along/cross: meters from the turn point along outBrg and to its side.
    static func frame(lat: Double, lon: Double, turnLat: Double, turnLon: Double, outBrg: Double) -> (along: Double, cross: Double) {
        let k = cos(turnLat * .pi / 180) * 111_320.0
        let x = (lon - turnLon) * k, y = (lat - turnLat) * 110_540.0, r = outBrg * .pi / 180
        return (x * sin(r) + y * cos(r), x * cos(r) - y * sin(r))
    }
    static func done(lat: Double, lon: Double, course: Double?, speed: Double, turnLat: Double, turnLon: Double, outBrg: Double?, arrive: Bool) -> Bool {
        if arrive { return CarPlayGeo.meters(lat, lon, turnLat, turnLon) < arriveM }
        guard let ob = outBrg else { return CarPlayGeo.meters(lat, lon, turnLat, turnLon) < arriveM }
        let f = frame(lat: lat, lon: lon, turnLat: turnLat, turnLon: turnLon, outBrg: ob)
        guard abs(f.cross) <= crossM, f.along >= pastM else { return false }
        if f.along >= sureM { return true }
        guard let c = course, speed >= 1 else { return false }
        return CarPlayGeo.diff(c, ob) <= headingDeg
    }
}

/// "Arrive at Destiny Coast" (Max t451u): the place name, else its address, else "destination".
enum CarPlayArrive {
    static func text(name: String?, address: String?) -> String {
        let n = (name ?? "").trimmingCharacters(in: .whitespaces), a = (address ?? "").trimmingCharacters(in: .whitespaces)
        let bad: Set<String> = ["", "Place", "Stop", "Dropped pin"]
        return "Arrive at " + (!bad.contains(n) ? n : !a.isEmpty ? a : "destination")
    }
}

/// Arrival celebration layout (Max t451u): ~15 s, banner centered in the CarPlay safe area (below the nav bar
/// buttons), never wider than the safe area.
enum CarPlayCelebrate {
    static let seconds = 15.0, reducedSeconds = 4.0
    static func bannerFrame(bounds: CGRect, safe: CGRect) -> CGRect {
        let s = safe.width > 0 && safe.height > 0 ? safe : bounds
        let w = min(s.width - 32, 520), h: CGFloat = s.height < 300 ? 52 : 64
        return CGRect(x: s.midX - w / 2, y: s.midY - h / 2, width: w, height: h).integral
    }
    /// Lanes for the unicorns: rows spread over the safe area, each a different speed, height and wave.
    static func lanes(count: Int, safe: CGRect) -> [(y: CGFloat, size: CGFloat, delay: Double, dur: Double, amp: CGFloat, rtl: Bool)] {
        (0..<count).map { i in
            let row = CGFloat(i % 4), size = min(96, safe.height / 4.2) * (i % 3 == 0 ? 1 : i % 3 == 1 ? 0.8 : 0.65)
            let y = safe.minY + 8 + row * (safe.height - size - 16) / 3
            return (y, size, Double(i) * 0.9, 3.2 + Double(i % 3) * 0.9, 10 + CGFloat(i % 4) * 6, i % 2 == 1)
        }
    }
}

/// CarPlay search list (Max t451u): Apple owns the keyboard and how many rows fit, so we keep rows short and
/// put the best matches first. Titles <= 28 chars, subtitles <= 32, at most 12 results.
enum CarPlaySearchText {
    static let titleMax = 28, subMax = 32, maxResults = 12
    static func clip(_ s: String?, _ n: Int) -> String? {
        guard let s = s?.trimmingCharacters(in: .whitespacesAndNewlines), !s.isEmpty else { return nil }
        return s.count <= n ? s : String(s.prefix(n - 1)).trimmingCharacters(in: .whitespaces) + "…"
    }
    /// Drops the country and ZIP from an Apple Maps address: "123 Main St, San Diego, CA 92109, United States" -> "123 Main St, San Diego".
    static func shortAddress(_ s: String?) -> String? {
        guard let s = s else { return nil }
        let parts = s.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
        return clip(parts.prefix(2).joined(separator: ", "), subMax)
    }
    /// Prefix matches first, then word-start matches, then the rest; nearer first within each group.
    static func rank(_ names: [(name: String, meters: Double?)], query: String) -> [Int] {
        let q = query.lowercased().trimmingCharacters(in: .whitespaces)
        func score(_ n: String) -> Int {
            let l = n.lowercased()
            if l.hasPrefix(q) { return 0 }
            if l.contains(" " + q) { return 1 }
            return 2
        }
        return names.indices.sorted { a, b in
            let sa = score(names[a].name), sb = score(names[b].name)
            if sa != sb { return sa < sb }
            return (names[a].meters ?? .infinity) < (names[b].meters ?? .infinity)
        }
    }
}
