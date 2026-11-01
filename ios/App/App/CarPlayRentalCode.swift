import Foundation

/// Rental code entry in CarPlay (Max t449u). Pure so ios/tests/main.swift can check it.
/// CarPlay has no free text field: the only typing is CPSearchTemplate, and the car can disable its keyboard
/// while driving (Apple's driver-distraction rules), so we always say where else to enter the code.
enum CarPlayRentalCode {
    static let phoneHint = "Enter your code in Settings in the phone app"
    /// Uppercase, no spaces or dashes; nil when it can't be a code. Matches public/rental.js normalize().
    static func normalize(_ s: String) -> String? {
        let c = s.uppercased().filter { !$0.isWhitespace && $0 != "-" }
        guard (4...16).contains(c.count), c.allSatisfy({ ("A"..."Z").contains(String($0)) || ("0"..."9").contains(String($0)) }) else { return nil }
        return c
    }
    /// Search results while typing: one "Unlock <CODE>" row once it looks like a code, else the phone hint.
    static func rows(for text: String) -> [(text: String, detail: String, code: String?)] {
        if let c = normalize(text) { return [("Unlock \(c)", "Uses your rental code once", c)] }
        return [("Type the code from your rental shop", phoneHint, nil)]
    }
}
