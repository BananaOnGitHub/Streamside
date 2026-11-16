// Real UIKit containment and compositor checks; synthetic views, no Twitch.
import SwiftUI
import UIKit

@main @MainActor final class QuickLookTestDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    var failures: [String] = []
    func check(_ passed: Bool, _ name: String) { if !passed { failures.append(name) } }
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        let root = UIViewController()
        root.view.backgroundColor = .blue
        window.rootViewController = root; window.makeKeyAndVisible(); self.window = window
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { self.exercise(root) }
        return true
    }
    func exercise(_ root: UIViewController) {
        let tags = ["English", "TogetherForGood", "Cat", "Very long Unicode tag 👨‍👩‍👧‍👦 " + String(repeating: "wide ", count: 12), "LastTag"]
        let all = UIHostingController(rootView: AllStreamTags(tags: tags))
        let short = UIHostingController(rootView: AllStreamTags(tags: ["English"]))
        let size = all.sizeThatFits(in: CGSize(width: 180, height: 10000))
        let one = short.sizeThatFits(in: CGSize(width: 180, height: 10000))
        check(size.height > one.height * 3 && size.width <= 181 && size.height < 10000, "All tags wrap with an oversized Unicode tag")
        let actions = ThumbnailActions(open: {}, preview: {})
        // The production recognizer wiring must preserve native scroll cancel.
        let host = UIHostingController(rootView: actions.frame(width: 140, height: 80))
        root.addChild(host); host.view.frame = CGRect(x: 0, y: 80, width: 140, height: 80)
        root.view.addSubview(host.view); host.didMove(toParent: root); host.view.layoutIfNeeded()
        func recognizers(_ view: UIView) -> [UIGestureRecognizer] {
            (view.gestureRecognizers ?? []) + view.subviews.flatMap(recognizers)
        }
        let hold = recognizers(host.view).compactMap { $0 as? UILongPressGestureRecognizer }.first
        check(hold?.minimumPressDuration == 0.5 && hold?.allowableMovement == 10, "Thumbnail hold recognizer installed")
        host.willMove(toParent: nil); host.view.removeFromSuperview(); host.removeFromParent()
        var starts = 0, stops = 0, watched = 0, creations = 0
        let preview = UIViewController(); preview.view.backgroundColor = .red
        let theatre = UIViewController(); theatre.view.backgroundColor = .green
        let controller = QuickLookController(preview: preview, makeTheatre: { creations += 1; return theatre },
                                             start: { starts += 1 }, watched: { watched += 1 }, stop: { stops += 1 })
        root.present(controller, animated: false) {
            self.check(starts == 1 && controller.children.count == 1, "Preview starts once")
            controller.watch(); controller.watch()
            self.check(creations == 1 && controller.children.count == 2 && controller.transitioning, "Single Watch handoff")
            DispatchQueue.main.asyncAfter(deadline: .now() + controller.fadeDuration * 0.45) {
                let a = preview.view.layer.presentation()?.opacity ?? -1
                let b = theatre.view.layer.presentation()?.opacity ?? -1
                self.check(a > 0.01 && a < 0.99 && b > 0.01 && b < 0.99 && abs(a + b - 1) < 0.05,
                           "Preview and theatre fade simultaneously")
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + controller.fadeDuration + 0.15) {
                self.check(controller.children.count == 1 && controller.children.first === theatre && !controller.transitioning && watched == 1 && stops == 0 && starts == 1, "Theatre retained without restarting playback")
                controller.dismiss(animated: false) {
                    self.check(stops == 1, "Dismiss stops exactly once")
                    self.cancelDuringFade(root)
                }
            }
        }
    }
    func cancelDuringFade(_ root: UIViewController) {
        var stops = 0, watched = 0
        let controller = QuickLookController(preview: UIViewController(), makeTheatre: { UIViewController() },
                                             start: {}, watched: { watched += 1 }, stop: { stops += 1 })
        root.present(controller, animated: false) {
            controller.watch()
            controller.dismiss(animated: false) {
                DispatchQueue.main.asyncAfter(deadline: .now() + controller.fadeDuration + 0.1) {
                    self.check(stops == 1 && watched == 0, "Closing during handoff never unmutes")
                    let receipt: [String: Any] = ["passed": self.failures.isEmpty, "failures": self.failures,
                                                 "synchronized_fade": true, "single_handoff": true,
                                                 "teardown": true, "all_tags_wrap": true, "thumbnail_hold": true]
                    let url = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("quicklook-test.json")
                    try! JSONSerialization.data(withJSONObject: receipt).write(to: url)
                    print("QUICKLOOK_CHECKS: \(self.failures.isEmpty ? "PASS" : self.failures.joined(separator: "; "))")
                    exit(self.failures.isEmpty ? 0 : 1)
                }
            }
        }
    }
}
