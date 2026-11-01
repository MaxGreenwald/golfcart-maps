import Foundation

/// Maps a shop link to the page the app loads from its own bundle (Max t448u).
/// Universal links: https://golfcartmap.com/p/<slug>[/go]?code= or ?handoff=, and /map?partner=&code=.
/// Custom scheme (the "Open in the app" button): golfcartmaps://p/<slug>/go?handoff=.
/// Returns a path + query for capacitor://localhost, or nil for links the app doesn't handle.
enum AppLinkRouter {
    static let hosts: Set<String> = ["golfcartmap.com", "www.golfcartmap.com"]
    static let scheme = "golfcartmaps"

    static func localPath(for url: URL) -> String? {
        guard let comps = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return nil }
        var parts = comps.path.split(separator: "/").map(String.init)
        switch comps.scheme?.lowercased() {
        case "https":
            guard let h = comps.host?.lowercased(), hosts.contains(h) else { return nil }
        case scheme:
            if let h = comps.host, !h.isEmpty { parts.insert(h, at: 0) }
        default:
            return nil
        }
        let q = Dictionary((comps.queryItems ?? []).compactMap { i in i.value.map { (i.name, $0) } }, uniquingKeysWith: { a, _ in a })
        if parts.first?.lowercased() == "p", parts.count >= 2 {
            let slug = parts[1].lowercased()
            guard isSlug(slug) else { return nil }
            return build("/p.html", [("slug", slug), ("code", q["code"]), ("handoff", q["handoff"])])
        }
        if parts == ["map"], let partner = q["partner"], isSlug(partner.lowercased()) {
            // Native build: index.html is the map.
            return build("/index.html", [("partner", partner.lowercased()), ("code", q["code"])])
        }
        return nil
    }

    static func isSlug(_ s: String) -> Bool {
        !s.isEmpty && s.count <= 64 && s.allSatisfy { ("a"..."z").contains(String($0)) || ("0"..."9").contains(String($0)) || $0 == "-" }
    }

    private static func build(_ path: String, _ items: [(String, String?)]) -> String {
        var c = URLComponents()
        c.path = path
        c.queryItems = items.compactMap { k, v in
            guard let v = v?.trimmingCharacters(in: .whitespaces), !v.isEmpty else { return nil }
            return URLQueryItem(name: k, value: v)
        }
        return c.string ?? path
    }
}
