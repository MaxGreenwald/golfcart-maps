import Foundation

/// When CarPlay speaks a maneuver (t455u). Same rule as the phone (public/navfollow.js promptPlan): once, about
/// 12 s before the turn at the current speed (35 to 180 m), or a short "Turn left onto X" at the turn (20 m) if that
/// moment was missed. Never the same maneuver twice. Foundation only so ios/tests/main.swift can run it on CI.
struct CarPlayVoicePlan {
    static let leadS = 12.0, minLeadM = 35.0, maxLeadM = 180.0, nowM = 20.0, defaultMS = 8.0, minSpeedMS = 1.0
    private var said = Set<String>()
    /// key: identifies the maneuver (survives reroutes, e.g. rounded turn coordinate). Returns what to say now, or nil.
    mutating func update(key: String, toNext: Double, speed: Double?, early: String, atTurn: String) -> String? {
        if said.contains(key) || !toNext.isFinite { return nil }
        let v = (speed ?? -1) > Self.minSpeedMS ? speed! : Self.defaultMS
        let lead = min(Self.maxLeadM, max(Self.minLeadM, v * Self.leadS))
        if toNext <= Self.nowM { said.insert(key); return atTurn }
        if toNext <= lead { said.insert(key); return early }
        return nil
    }
    /// Mark a maneuver as already announced (e.g. the first instruction spoken at Start).
    mutating func markSaid(_ key: String) { said.insert(key) }
    mutating func reset() { said.removeAll() }
    /// "In 300 feet, turn left onto Garnet Avenue" (feet under 0.1 mi, rounded to 50; then tenths of a mile).
    static func early(_ short: String, meters: Double) -> String {
        guard let f = short.first else { return short }
        let rest = f.lowercased() + short.dropFirst(), ft = meters * 3.28084
        let d = ft < 528 ? "\(max(50, Int((ft / 50).rounded()) * 50)) feet" : String(format: "%.1f miles", ft / 5280)
        return "In \(d), \(rest)"
    }
}

/// Voice guidance setting shared by the phone nav screen and CarPlay (default ON).
enum GCMVoiceSetting {
    static let key = "gcm_voice_muted"
    static func isMuted(_ d: UserDefaults = .standard) -> Bool { d.bool(forKey: key) }
    static func setMuted(_ m: Bool, _ d: UserDefaults = .standard) { d.set(m, forKey: key) }
}
