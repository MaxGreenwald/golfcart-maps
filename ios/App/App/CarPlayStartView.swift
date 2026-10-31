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

    /// Map frame that fills `bounds` but whose center (where follow mode draws the dot) is inside `safe`,
    /// 10% of the safe height below its middle, so the guidance card never covers the dot.
    static func mapFrame(bounds b: CGRect, safe: CGRect) -> CGRect {
        let cx = safe.midX, cy = min(safe.maxY, safe.midY + safe.height * 0.1)
        let hw = max(cx - b.minX, b.maxX - cx), hh = max(cy - b.minY, b.maxY - cy)
        return CGRect(x: cx - hw, y: cy - hh, width: hw * 2, height: hh * 2)
    }
}
