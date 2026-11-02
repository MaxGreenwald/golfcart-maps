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

/// Reroute telemetry (t453u): what the shared engine decided on each notable fix and what the bridge answered.
/// The scene delegate NSLogs each line and keeps the last 200 in UserDefaults (key below) for a TestFlight readout.
struct CarPlayNavLog {
    static let key = "gcm_cp_navlog", max = 200
    private(set) var lines: [String]
    init(lines: [String] = []) { self.lines = lines }
    mutating func add(_ s: String, at t: Date = Date()) {
        let f = DateFormatter(); f.dateFormat = "HH:mm:ss"; f.timeZone = TimeZone(identifier: "America/Los_Angeles")
        lines.append(f.string(from: t) + " PT " + s)
        if lines.count > Self.max { lines.removeFirst(lines.count - Self.max) }
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
    /// Two lines (Max t454u: one line was cut off on both sides on a wide CarPlay screen).
    static let line1 = "You have Arrived!", line2 = "Have a wonderful life you LEGEND 🦄"
    static let padX: CGFloat = 16, padY: CGFloat = 8
    static func bannerFrame(bounds: CGRect, safe: CGRect) -> CGRect {
        let s = safe.width > 0 && safe.height > 0 ? safe : bounds
        let w = min(s.width - 32, 560), h: CGFloat = min(s.height - 16, s.height < 300 ? 84 : 104)
        return CGRect(x: s.midX - w / 2, y: s.midY - h / 2, width: w, height: h).integral
    }
    /// Largest point sizes (title, subtitle) so both lines fit inside the banner minus padding.
    /// `measure(text, size)` returns the drawn width of text at that size (UIFont heavy in the app).
    static func fontSizes(banner: CGRect, measure: (String, CGFloat) -> CGFloat) -> (title: CGFloat, sub: CGFloat) {
        let innerW = banner.width - 2 * padX, innerH = banner.height - 2 * padY
        var t: CGFloat = 30
        while t > 8 {
            let sub = t * 0.72
            if measure(line1, t) <= innerW && measure(line2, sub) <= innerW && (t + sub) * 1.22 <= innerH { break }
            t -= 0.5
        }
        return (t, t * 0.72)
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

/// CarPlay follow camera (t456u-t458u). Build 42 re-enabled MKMapView's own .follow tracking after every zoom and on
/// every guidance tick; MapKit re-zooms to its default when tracking turns on, so + / - and panning snapped back.
/// Now we move the camera ourselves: the driver's zoom (camera distance) persists, panning pauses follow, and
/// follow resumes on the recenter button or after `idleResume` seconds without touching the map.
struct CarPlayFollow {
    static let minM = 150.0, maxM = 60_000.0, idleResume = 12.0
    var following = false
    var userDistance: Double?          // set by + / -; kept through nav, reroutes and recenter
    var pausedAt: Double?
    /// Camera distance to use: the driver's choice, else the default for this view.
    func distance(default d: Double) -> Double { userDistance ?? d }
    /// + is factor 0.5, - is 2; clamped.
    mutating func zoom(current: Double, factor: Double) -> Double {
        let d = min(Self.maxM, max(Self.minM, current * factor)); userDistance = d; return d
    }
    mutating func pan(now: Double) { following = false; pausedAt = now }
    mutating func resume() { following = true; pausedAt = nil }
    /// True once when a pan pause has been idle long enough.
    mutating func shouldAutoResume(now: Double) -> Bool {
        guard !following, let p = pausedAt, now - p >= Self.idleResume else { return false }
        resume(); return true
    }
}
