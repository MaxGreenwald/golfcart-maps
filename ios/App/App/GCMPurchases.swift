import Foundation
import Capacitor
import StoreKit

/// Driver plan in-app purchases (StoreKit 2). JS side: public/entitlements.js (window.GCMEnt).
/// Only extra towns, offline maps and voice routing are paid. The core legal-roads map is never gated.
/// StoreKit 2 needs iOS 15; on iOS 14 every call answers "not available" and nothing is unlocked or locked by it.
@objc(GCMPurchases)
public class GCMPurchases: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "GCMPurchases"
    public let jsName = "GCMPurchases"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "getProducts", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "purchase", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "restore", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "getEntitlement", returnType: CAPPluginReturnPromise),
    ]

    static let productIDs = ["com.matchimus.golfcartmaps.driver.monthly", "com.matchimus.golfcartmaps.driver.yearly"]
    private var updates: Task<Void, Never>?

    override public func load() {
        if #available(iOS 15.0, *) {
            updates = Task.detached { [weak self] in
                for await result in Transaction.updates {
                    if case .verified(let t) = result { await t.finish() }
                    await self?.pushEntitlement()
                }
            }
        }
    }

    deinit { updates?.cancel() }

    @objc func getProducts(_ call: CAPPluginCall) {
        guard #available(iOS 15.0, *) else { call.resolve(["products": []]); return }
        let ids = call.getArray("ids", String.self) ?? Self.productIDs
        Task {
            do {
                let ps = try await Product.products(for: ids.filter { Self.productIDs.contains($0) })
                call.resolve(["products": ps.map { ["id": $0.id, "displayPrice": $0.displayPrice, "displayName": $0.displayName] }])
            } catch { call.resolve(["products": []]) }
        }
    }

    @objc func purchase(_ call: CAPPluginCall) {
        guard #available(iOS 15.0, *) else { call.reject("unavailable"); return }
        guard let id = call.getString("id"), Self.productIDs.contains(id) else { call.reject("unknown product"); return }
        Task {
            do {
                guard let p = try await Product.products(for: [id]).first else { call.reject("unknown product"); return }
                switch try await p.purchase() {
                case .success(let v):
                    if case .verified(let t) = v { await t.finish() }
                    var r = await Self.entitlement(); r["ok"] = true; call.resolve(r)
                case .pending: call.resolve(["ok": false, "pending": true, "paid": false])
                case .userCancelled: call.resolve(["ok": false, "cancelled": true, "paid": false])
                @unknown default: call.resolve(["ok": false, "paid": false])
                }
            } catch { call.reject("purchase failed") }
        }
    }

    @objc func restore(_ call: CAPPluginCall) {
        guard #available(iOS 15.0, *) else { call.resolve(["ok": false, "paid": false]); return }
        Task {
            try? await AppStore.sync()
            var r = await Self.entitlement(); r["ok"] = true; call.resolve(r)
        }
    }

    @objc func getEntitlement(_ call: CAPPluginCall) {
        guard #available(iOS 15.0, *) else { call.resolve(["paid": false]); return }
        Task { call.resolve(await Self.entitlement()) }
    }

    @available(iOS 15.0, *)
    static func entitlement() async -> [String: Any] {
        for await result in Transaction.currentEntitlements {
            guard case .verified(let t) = result, productIDs.contains(t.productID), t.revocationDate == nil else { continue }
            if let e = t.expirationDate, e < Date() { continue }
            var r: [String: Any] = ["paid": true, "product": t.productID]
            if let e = t.expirationDate { r["expires"] = ISO8601DateFormatter().string(from: e) }
            return r
        }
        return ["paid": false]
    }

    /// Tells the web app (GCMEnt) when a renewal, refund or purchase on another device changes the entitlement.
    @available(iOS 15.0, *)
    func pushEntitlement() async {
        let r = await Self.entitlement()
        notifyListeners("entitlement", data: r)
        guard let data = try? JSONSerialization.data(withJSONObject: r), let json = String(data: data, encoding: .utf8) else { return }
        await MainActor.run {
            _ = self.bridge?.webView?.evaluateJavaScript("window.dispatchEvent(new CustomEvent('gcm:native-entitlement',{detail:\(json)}))")
        }
    }
}

/// Phone view controller: Capacitor's bridge plus the app's own plugins.
class GCMBridgeViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        bridge?.registerPluginInstance(GCMPurchases())
    }
}
