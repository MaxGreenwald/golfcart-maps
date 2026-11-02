import UIKit
import AVFoundation
import WebKit
import Capacitor

/// Spoken turn-by-turn directions (Max t455u: "audible instructions don't work when I'm playing music in CarPlay").
/// The web app used speechSynthesis inside WKWebView, which plays on an ambient audio session: Spotify drowns it or it
/// is dropped, and nothing plays while the phone is locked for CarPlay. Like Google Maps, we now speak natively on a
/// voice-prompt session that ducks music (and pauses spoken audio such as podcasts), then hands audio back.
/// Mute (GCMVoiceSetting) is one switch for the phone nav screen and CarPlay.
final class GCMVoice: NSObject, AVSpeechSynthesizerDelegate, WKScriptMessageHandler {
    static let shared = GCMVoice()
    static let mutedChanged = Notification.Name("GCMVoiceMutedChanged")
    private let synth = AVSpeechSynthesizer()
    private var webIds: [ObjectIdentifier: (Int, WeakWebView)] = [:]   // utterance -> web caller to notify
    private var attached = Set<ObjectIdentifier>()
    private var lastText = "", lastAt = Date.distantPast
    private let audioQ = DispatchQueue(label: "gcm.voice.audio")

    final class WeakWebView { weak var wv: WKWebView?; init(_ w: WKWebView) { wv = w } }

    override init() {
        super.init()
        synth.delegate = self
        synth.usesApplicationAudioSession = true
        if #available(iOS 14.0, *) { synth.prefersAssistiveTechnologySettings = false }
    }

    var muted: Bool {
        get { GCMVoiceSetting.isMuted() }
        set {
            GCMVoiceSetting.setMuted(newValue)
            if newValue { stop() }
            pushMuteToWeb()
            NotificationCenter.default.post(name: Self.mutedChanged, object: nil)
        }
    }

    /// Lets a Capacitor web view (phone UI or the headless CarPlay one) speak through us: window.webkit.messageHandlers.gcmvoice.
    func attach(_ wv: WKWebView) {
        let k = ObjectIdentifier(wv)
        if attached.contains(k) { return }
        attached.insert(k)
        wv.configuration.userContentController.add(self, name: "gcmvoice")
        // Start the page with the native setting (the web view's localStorage may be older).
        let js = "try{localStorage.setItem('\(GCMVoiceSetting.key)','\(muted ? "1" : "0")')}catch(e){};"
        wv.configuration.userContentController.addUserScript(WKUserScript(source: js, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        webViews.append(WeakWebView(wv))
        pushMuteToWeb()
    }
    private var webViews: [WeakWebView] = []
    private func pushMuteToWeb() {
        let js = "window.GCMFollow&&GCMFollow.setMuted(\(muted),true);try{localStorage.setItem('\(GCMVoiceSetting.key)','\(muted ? "1" : "0")')}catch(e){};0"
        webViews.removeAll { $0.wv == nil }
        for w in webViews { w.wv?.evaluateJavaScript(js, completionHandler: nil) }
    }

    func userContentController(_ c: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let d = message.body as? [String: Any] else { return }
        if let m = d["mute"] as? Bool { if m != muted { muted = m }; return }
        if d["stop"] != nil { stop(); return }
        if let t = d["say"] as? String {
            let id = (d["id"] as? NSNumber)?.intValue ?? 0
            let wv = message.webView
            if !speak(t, notify: wv.map { (id, WeakWebView($0)) }) { finishWeb(id, wv) }
        }
    }

    /// Speaks one sentence unless muted. The same sentence from the phone and CarPlay within 8 s is said once.
    /// Returns false if nothing was queued.
    @discardableResult
    func speak(_ text: String, notify: (Int, WeakWebView)? = nil) -> Bool {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if t.isEmpty || muted { return false }
        if t == lastText, Date().timeIntervalSince(lastAt) < 8 { return false }
        lastText = t; lastAt = Date()
        activate()
        let u = AVSpeechUtterance(string: t)
        u.voice = AVSpeechSynthesisVoice(language: AVSpeechSynthesisVoice.currentLanguageCode())
        u.rate = AVSpeechUtteranceDefaultSpeechRate
        u.prefersAssistiveTechnologySettings = false
        if let n = notify { webIds[ObjectIdentifier(u)] = n }
        synth.speak(u)
        #if DEBUG
        NSLog("GCMVoice say: %@", t)
        #endif
        return true
    }

    func stop() { synth.stopSpeaking(at: .immediate) }

    // Category .playback (plays with the silent switch on and in the background, UIBackgroundModes audio), mode
    // .voicePrompt (CarPlay routes it as navigation audio), duck music and interrupt spoken audio while talking.
    private func activate() {
        audioQ.async {
            let s = AVAudioSession.sharedInstance()
            do {
                try s.setCategory(.playback, mode: .voicePrompt, options: [.duckOthers, .interruptSpokenAudioAndMixWithOthers])
                try s.setActive(true)
            } catch { NSLog("GCMVoice audio session: %@", error.localizedDescription) }
        }
    }
    private func deactivateIfIdle() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { [weak self] in
            guard let self = self, !self.synth.isSpeaking else { return }
            self.audioQ.async {   // music comes back to full volume
                try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
            }
        }
    }

    private func finished(_ u: AVSpeechUtterance) {
        if let (id, w) = webIds.removeValue(forKey: ObjectIdentifier(u)) { finishWeb(id, w.wv) }
        deactivateIfIdle()
    }
    private func finishWeb(_ id: Int, _ wv: WKWebView?) {
        wv?.evaluateJavaScript("window.__gcmVoiceDone&&__gcmVoiceDone(\(id));0", completionHandler: nil)
    }
    func speechSynthesizer(_ s: AVSpeechSynthesizer, didFinish u: AVSpeechUtterance) { finished(u) }
    func speechSynthesizer(_ s: AVSpeechSynthesizer, didCancel u: AVSpeechUtterance) { finished(u) }
}

/// Main.storyboard's view controller: the stock Capacitor one plus native voice for the web app.
class GCMViewController: CAPBridgeViewController {
    override func capacitorDidLoad() {
        super.capacitorDidLoad()
        if let wv = bridge?.webView { GCMVoice.shared.attach(wv) }
    }
}
