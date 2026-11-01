import UIKit
import Capacitor
import WebKit

/// Phone window scene. Loads Main.storyboard (CAPBridgeViewController) via the scene manifest.
/// Shop links (universal links and golfcartmaps://) open the bundled shop page (Max t448u).
class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        // Cold launch from a link: the bridge isn't up yet, so openAppLink waits for it.
        for a in connectionOptions.userActivities { if let u = a.webpageURL, openAppLink(u) { return } }
        for c in connectionOptions.urlContexts { if openAppLink(c.url) { return } }
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        for ctx in URLContexts {
            if openAppLink(ctx.url) { continue }
            _ = ApplicationDelegateProxy.shared.application(UIApplication.shared, open: ctx.url, options: [:])
        }
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        if let u = userActivity.webpageURL, openAppLink(u) { return }
        _ = ApplicationDelegateProxy.shared.application(UIApplication.shared, continue: userActivity, restorationHandler: { _ in })
    }

    /// Loads the mapped page in the phone web view. False when the link isn't a shop link.
    @discardableResult
    func openAppLink(_ url: URL) -> Bool {
        guard let path = AppLinkRouter.localPath(for: url) else { return false }
        load(path, tries: 40)
        return true
    }

    private func load(_ path: String, tries: Int) {
        let vc = window?.rootViewController as? CAPBridgeViewController
        // iOS Capacitor serves the bundle at capacitor://localhost (no server.url in capacitor.config.json).
        if let wv = vc?.bridge?.webView, let url = URL(string: "capacitor://localhost" + path) {
            wv.load(URLRequest(url: url))
            return
        }
        guard tries > 0 else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { [weak self] in self?.load(path, tries: tries - 1) }
    }
}
