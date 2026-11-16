import CarPlay
import UIKit

/// CarPlay-only Help control. Phone and web render the button in the page (`public/help.js`).
/// This asks the shared web layer for the shop number and the message (location already in the text),
/// then shows Call and Text. It does not choose roads, turns, or when you have arrived.
enum RenterHelp {
    static func barButton(bridge: RenterHelpBridge) -> CPBarButton {
        CPBarButton(title: "Help") { _ in
            bridge.currentFix { lat, lon in
                bridge.help(lat: lat, lon: lon) { result in
                    guard result.ok, let tel = result.tel, let sms = result.sms else {
                        bridge.presentAlert(title: "This shop has no phone number yet.", actions: [
                            CPAlertAction(title: "OK", style: .cancel) { _ in },
                        ])
                        return
                    }
                    let call = CPAlertAction(title: "Call shop", style: .default) { _ in bridge.open(tel) }
                    let text = CPAlertAction(title: "Text my location", style: .default) { _ in bridge.open(sms) }
                    let cancel = CPAlertAction(title: "Cancel", style: .cancel) { _ in }
                    bridge.presentAlert(title: "Help", actions: [call, text, cancel])
                }
            }
        }
    }
}

protocol RenterHelpBridge: AnyObject {
    func currentFix(_ done: @escaping (Double?, Double?) -> Void)
    func help(lat: Double?, lon: Double?, done: @escaping (RenterHelpResult) -> Void)
    func open(_ url: URL)
    func presentAlert(title: String, actions: [CPAlertAction])
}

struct RenterHelpResult {
    var ok: Bool
    var tel: URL?
    var sms: URL?
}
