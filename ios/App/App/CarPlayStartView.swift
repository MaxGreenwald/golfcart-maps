import Foundation

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
