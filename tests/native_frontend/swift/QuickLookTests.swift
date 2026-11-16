// Owned UIKit transaction/target tests. Real anchored-preview/video UI is exercised
// separately by PlayerInputTests; this executable never claims donor playback.
import SwiftUI
import UIKit

@MainActor private final class HeldPresentationCompletion {
    var completions: [() -> Void] = []
    func addCompletion(_ completion: @escaping () -> Void) { completions.append(completion) }
    func finish() { completions.forEach { $0() }; completions = [] }
}

@main @MainActor final class QuickLookTestDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    var failures: [String] = []
    func check(_ condition: Bool, _ name: String) { if !condition { failures.append(name) } }
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = UIViewController(); window.makeKeyAndVisible(); self.window = window
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { self.exercise() }
        return true
    }
    func exercise() {
        let tags = ["English", "TogetherForGood", "Cat", String(repeating: "Unicode 👨‍👩‍👧‍👦 ", count: 12), "LastTag"]
        let all = UIHostingController(rootView: AllStreamTags(tags: tags))
        let short = UIHostingController(rootView: AllStreamTags(tags: ["English"]))
        let size = all.sizeThatFits(in: CGSize(width: 180, height: 10000))
        let one = short.sizeThatFits(in: CGSize(width: 180, height: 10000))
        check(size.height > one.height * 3 && size.width <= 181, "All admitted tags wrap")
        let controller = UIViewController()
        var starts = 0, stops = 0, handoffs = 0, releases = 0
        let session = ContextPreviewSession(controller: controller, claim: { _ in true }, release: { _ in releases += 1 },
            valid: { true }, start: { starts += 1 }, stop: { stops += 1 }, handoff: { handoffs += 1; return true })
        check(session.display() && session.display() && starts == 1, "Start once")
        session.requestWatch(); session.requestWatch()
        let animator = HeldPresentationCompletion()
        session.end(after: animator.addCompletion); session.end(after: animator.addCompletion)
        check(handoffs == 0 && stops == 0 && releases == 0, "No handoff before presentation finishes")
        animator.finish()
        DispatchQueue.main.async {
            self.check(session.phase == .transferred && handoffs == 1 && starts == 1 && stops == 0 && releases == 1, "One ownership transfer")
            session.cancel()
            self.check(stops == 0, "Transferred player belongs to theatre")
            self.cancelWhileEnding()
        }
    }
    func cancelWhileEnding() {
        var starts = 0, stops = 0, handoffs = 0, dismissals = 0
        let controller = UIViewController()
        let session = ContextPreviewSession(controller: controller, claim: { _ in true }, release: { _ in }, valid: { true },
            start: { starts += 1 }, stop: { stops += 1 }, handoff: { handoffs += 1; return true })
        session.dismissPreview = { dismissals += 1 }
        session.display(); session.requestWatch()
        let animator = HeldPresentationCompletion(); session.end(after: animator.addCompletion)
        session.cancel(); session.cancel(); animator.finish()
        DispatchQueue.main.async {
            self.check(starts == 1 && stops == 1 && handoffs == 0 && dismissals == 0 && session.phase == .cancelled, "Cancellation during dismissal cannot watch or unmute")
            self.backgroundAndAccount()
        }
    }
    func backgroundAndAccount() {
        var valid = true, stops = 0
        let session = ContextPreviewSession(controller: UIViewController(), claim: { _ in true }, release: { _ in }, valid: { valid }, start: {}, stop: { stops += 1 }, handoff: { false })
        session.display(); valid = false
        NotificationCenter.default.post(name: Notification.Name("SSNNativeServiceDidChange"), object: nil)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            self.check(stops == 1 && session.phase == .cancelled, "Account invalidation cancels")
            let background = ContextPreviewSession(controller: UIViewController(), claim: { _ in true }, release: { _ in }, valid: { true }, start: {}, stop: { stops += 1 }, handoff: { false })
            background.display()
            NotificationCenter.default.post(name: UIApplication.willResignActiveNotification, object: nil)
            self.check(stops == 2 && background.phase == .cancelled, "Background cancels")
            self.rejectedAndLateActions()
        }
    }
    func rejectedAndLateActions() {
        var starts = 0, stops = 0, releases = 0, handoffs = 0
        let rejected = ContextPreviewSession(controller: UIViewController(), claim: { _ in false }, release: { _ in releases += 1 }, valid: { true },
            start: { starts += 1 }, stop: { stops += 1 }, handoff: { handoffs += 1; return true })
        check(!rejected.display() && starts == 0 && stops == 1 && releases == 1, "Rejected ownership cleans prepared resources")
        let controller = UIViewController()
        let late = ContextPreviewSession(controller: controller, claim: { _ in true }, release: { _ in releases += 1 }, valid: { true },
            start: { starts += 1 }, stop: { stops += 1 }, handoff: { handoffs += 1; return false })
        late.display()
        let animator = HeldPresentationCompletion()
        late.end(after: animator.addCompletion); late.requestWatch(); animator.finish()
        DispatchQueue.main.async {
            self.check(starts == 1 && stops == 2 && releases == 2 && handoffs == 1 && late.phase == .cancelled, "Action delivered during dismissal and rejected handoff clean once")
            self.sourceTarget()
        }
    }
    func sourceTarget() {
        guard let root = window?.rootViewController else { fatalError("Missing fixture root") }
        let source = ThumbnailActions.SourceView(frame: CGRect(x: 45, y: 560, width: 160, height: 90))
        let scroll = UIScrollView(frame: root.view.bounds)
        scroll.contentInsetAdjustmentBehavior = .never
        scroll.contentSize = CGSize(width: root.view.bounds.width, height: 1800)
        root.view.addSubview(scroll); scroll.addSubview(source)
        scroll.contentOffset = CGPoint(x: 0, y: 300)
        let actual = source.convert(source.bounds, to: root.view)
        check(abs(actual.minX - 45) < 0.5 && abs(actual.minY - 260) < 0.5 && actual.width == 160, "Geometry follows actual scroll offset")
        let collapsed = PreviewPlacement.collapsedCenter(source: actual, card: CGSize(width: 370, height: 500))
        let scale = actual.width / 370
        check(abs(collapsed.y - 500 * scale / 2 - actual.minY) < 0.5 && abs(370 * 9 / 16 * scale - actual.height) < 0.5, "Collapsed video aligns exactly with source thumbnail")
        let viewport = CGRect(x: 16, y: 62, width: 370, height: 760)
        for position in [actual, actual.offsetBy(dx: 0, dy: -300), actual.offsetBy(dx: 0, dy: 1000)] {
            if let placement = PreviewPlacement.make(viewport: viewport, source: position, card: CGSize(width: 370, height: 600), menu: CGSize(width: 270, height: 112)) {
                check(viewport.contains(placement.card) && viewport.contains(placement.menu) && placement.menu.minY >= placement.card.maxY + 14, "Card and separate menu stay within safe viewport")
                check(placement.card.width == 370 && placement.card.height >= 370 * 9 / 16 + 44, "Placement reserves a 16:9 player and usable details")
            } else { check(false, "Expected valid placement") }
        }
        check(PreviewPlacement.make(viewport: CGRect(x: 0, y: 0, width: 200, height: 100), source: actual,
            card: CGSize(width: 370, height: 400), menu: CGSize(width: 270, height: 112)) == nil, "Reject impossible geometry")
        // Verify public UIKit containment and cancellation cleanup without a modal.
        let content = QuickLookController(content: UIViewController(), size: CGSize(width: 370, height: 360))
        var targets: [Bool] = []
        let preview = AnchoredPreviewController(content: content, source: source, watch: {}, dismiss: {}, observeTarget: { ending, frame, center in
            self.check(abs(frame.midX - center.x) < 0.5 && abs(frame.midY - center.y) < 0.5, "Animation uses actual source center")
            targets.append(ending)
        })
        check(preview.install(in: root), "Install root child")
        check(preview.parent === root && root.presentedViewController == nil && source.isHidden, "Child ownership preserves root and lifts source")
        preview.dismiss(watching: false) {
            self.check(preview.parent == nil && !source.isHidden && targets == [false, true], "Interrupted lift restores source and detaches once")
            self.finishReceipt()
        }
    }
    func finishReceipt() {
        let receipt: [String: Any] = ["passed": failures.isEmpty, "failures": failures, "source_target": true,
            "dismiss_before_handoff": true, "single_handoff": true, "teardown": true, "all_tags_wrap": true, "lifecycle_cancellation": true]
        let path = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("quicklook-test.json")
        try! JSONSerialization.data(withJSONObject: receipt).write(to: path)
        print("QUICKLOOK_CHECKS: \(failures.isEmpty ? "PASS" : failures.joined(separator: "; "))")
        exit(failures.isEmpty ? 0 : 1)
    }
}
