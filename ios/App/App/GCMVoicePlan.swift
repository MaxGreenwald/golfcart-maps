import Foundation

// Turn-timing for speech lives in the shared phone engine (public/carplay.js navFix `say`, AGENTS.md rule 35).

/// Voice guidance setting shared by the phone nav screen and CarPlay (default ON).
enum GCMVoiceSetting {
    static let key = "gcm_voice_muted"
    static func isMuted(_ d: UserDefaults = .standard) -> Bool { d.bool(forKey: key) }
    static func setMuted(_ m: Bool, _ d: UserDefaults = .standard) { d.set(m, forKey: key) }
}
