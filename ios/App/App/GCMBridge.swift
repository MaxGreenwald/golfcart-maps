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

    // Results come back through a WKScriptMessageHandler. (We avoid the Swift-overlay
    // callAsyncJavaScript/Result API: it pulls in libswiftWebKit.dylib, which older iOS runtimes lack.)
    private var pending: [Int: (Any?) -> Void] = [:]
    private var nextId = 1
    private var registered = Set<ObjectIdentifier>()
    private lazy var handler = Handler(owner: self)

    final class Handler: NSObject, WKScriptMessageHandler {
        weak var owner: GCMBridge?
        init(owner: GCMBridge) { self.owner = owner }
        func userContentController(_ c: WKUserContentController, didReceive message: WKScriptMessage) {
            guard let d = message.body as? [String: Any], let id = (d["id"] as? NSNumber)?.intValue,
                  let cb = owner?.pending.removeValue(forKey: id) else { return }
            var v: Any? = nil
            if let s = d["r"] as? String, let data = s.data(using: .utf8) {
                v = try? JSONSerialization.jsonObject(with: data, options: [.fragmentsAllowed])
            }
            if v is NSNull { v = nil }
            cb(v)
        }
    }

    /// Runs `await GCMCarPlay.<body>` with named JSON arguments; `done` gets the decoded JSON (main thread).
    func call(_ body: String, _ args: [String: Any] = [:], done: @escaping (Any?) -> Void) {
        guard let wv = webView else { done(nil); return }
        let key = ObjectIdentifier(wv)
        if !registered.contains(key) {
            wv.configuration.userContentController.add(handler, name: "gcmcp")
            registered.insert(key)
        }
        let id = nextId; nextId += 1
        pending[id] = done
        var decl = ""
        for (k, v) in args {
            guard JSONSerialization.isValidJSONObject([v]),
                  let data = try? JSONSerialization.data(withJSONObject: [v]),
                  let json = String(data: data, encoding: .utf8) else { continue }
            decl += "const \(k)=\(json)[0];"
        }
        let js = "(async()=>{let r=null;try{\(decl)for(let i=0;i<600&&!window.GCMCarPlay;i++)await new Promise(z=>setTimeout(z,50));if(window.GCMCarPlay)r=await GCMCarPlay.\(body);}catch(e){console.error('GCMCarPlay',e)}window.webkit.messageHandlers.gcmcp.postMessage({id:\(id),r:JSON.stringify(r===undefined?null:r)})})();0"
        wv.evaluateJavaScript(js) { [weak self] _, err in
            if let err = err {
                NSLog("GCMBridge %@ failed: %@", body, err.localizedDescription)
                if let cb = self?.pending.removeValue(forKey: id) { cb(nil) }
            }
        }
    }

    /// Analytics hook for CarPlay (public/carplay.js GCMCarPlay.track -> public/track.js). Town level only, anonymous
    /// install id, platform "carplay"; the web layer drops it under GPC/Do Not Track/opt-out. Allowed: session,
    /// route_started, route_completed (mi rounded to 0.5). DEBUG builds log the result so the simulator run can check it.
    func track(_ name: String, _ props: [String: Any] = [:]) {
        call("track(n,p)", ["n": name, "p": props]) { any in
            #if DEBUG
            let ok = (any as? [String: Any])?["ok"] as? Bool ?? false
            NSLog("GCMTrack %@ %@", name, ok ? "ok" : "failed: \(String(describing: any))")
            #endif
        }
    }
}
