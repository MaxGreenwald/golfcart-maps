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
