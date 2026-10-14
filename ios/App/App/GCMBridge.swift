import UIKit
import WebKit
import Capacitor

/// Calls the web app's routing engine (public/carplay.js -> window.GCMCarPlay) from native code.
/// CarPlay reuses the exact same rules, road data and A* router as the phone/web app, so there is
/// only one routing implementation to keep correct. If the phone UI isn't running (CarPlay-only
/// launch), a headless Capacitor web view is created and parked inside the CarPlay window.
final class GCMBridge {
    static let shared = GCMBridge()
    private var headless: CAPBridgeViewController?

    /// Web view of the phone scene, if it's connected.
    private func phoneWebView() -> WKWebView? {
        for scene in UIApplication.shared.connectedScenes {
            guard let ws = scene as? UIWindowScene, ws.session.role == .windowApplication else { continue }
            for w in ws.windows {
                if let vc = w.rootViewController as? CAPBridgeViewController, let wv = vc.bridge?.webView { return wv }
            }
        }
        return nil
    }

    /// Ensures a web view exists. `host` is a view to park a headless web view in so WebKit keeps running JS.
    func attachHeadlessIfNeeded(to host: UIView) {
        if phoneWebView() != nil || headless != nil { return }
        let vc = CAPBridgeViewController()
        vc.loadViewIfNeeded()
        vc.view.frame = CGRect(x: 0, y: 0, width: 2, height: 2)
        vc.view.alpha = 0.01
        vc.view.isUserInteractionEnabled = false
        host.addSubview(vc.view)
        host.sendSubviewToBack(vc.view)
        headless = vc
    }

    private var webView: WKWebView? { phoneWebView() ?? headless?.bridge?.webView }

    /// Runs `return await GCMCarPlay.<body>` with named JSON arguments.
    func call(_ body: String, _ args: [String: Any] = [:], done: @escaping (Any?) -> Void) {
        guard let wv = webView else { done(nil); return }
        let js = "for(let i=0;i<600&&!window.GCMCarPlay;i++)await new Promise(r=>setTimeout(r,50));if(!window.GCMCarPlay)return null;return await GCMCarPlay.\(body);"
        wv.callAsyncJavaScript(js, arguments: args, in: nil, in: .page) { result in
            switch result {
            case .success(let v): done(v)
            case .failure(let e): NSLog("GCMBridge %@ failed: %@", body, e.localizedDescription); done(nil)
            }
        }
    }
}
