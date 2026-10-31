import UIKit
import Capacitor

/// Phone window scene. Main.storyboard (CAPBridgeViewController) still provides the window via the
/// scene manifest (UISceneStoryboardFile). Capacitor 8.5 (UIScene lifecycle, needed for Xcode 27):
/// scene callbacks go through SceneDelegateProxy so appUrlOpen, getLaunchUrl and pause/resume keep working.
/// The CarPlay scene has its own delegate (CarPlaySceneDelegate) and is not routed here.
class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        SceneDelegateProxy.shared.scene(scene, willConnectTo: session, options: connectionOptions)
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        SceneDelegateProxy.shared.scene(scene, openURLContexts: URLContexts)
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        SceneDelegateProxy.shared.scene(scene, continue: userActivity)
    }
}
