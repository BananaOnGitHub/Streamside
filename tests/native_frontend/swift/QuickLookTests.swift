// Owned UIKit transaction/target tests. Real context-menu/video UI is exercised
// separately by PlayerInputTests; this executable never claims donor playback.
import SwiftUI
import UIKit

@MainActor private final class HeldMenuAnimator: NSObject, UIContextMenuInteractionAnimating {
    let previewViewController: UIViewController?
    var animations: [() -> Void] = []
    var completions: [() -> Void] = []
    init(_ preview: UIViewController) { previewViewController = preview }
    func addAnimations(_ animations: @escaping () -> Void) { self.animations.append(animations) }
    func addCompletion(_ completion: @escaping () -> Void) { completions.append(completion) }
    func finish() { animations.forEach { $0() }; completions.forEach { $0() }; completions = [] }
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
        let animator = HeldMenuAnimator(controller)
        session.end(animator: animator); session.end(animator: animator)
        check(handoffs == 0 && stops == 0 && releases == 0, "No handoff before UIKit finishes")
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
        session.dismissMenu = { dismissals += 1 }
        session.display(); session.requestWatch()
        let animator = HeldMenuAnimator(controller); session.end(animator: animator)
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
        let animator = HeldMenuAnimator(controller)
        late.end(animator: animator); late.requestWatch(); animator.finish()
        DispatchQueue.main.async {
            self.check(starts == 1 && stops == 2 && releases == 2 && handoffs == 1 && late.phase == .cancelled, "Action delivered during dismissal and rejected handoff clean once")
            self.sourceTarget()
        }
    }
    func sourceTarget() {
        guard let root = window?.rootViewController else { fatalError("Missing fixture root") }
        var observations = 0
        let actions = ThumbnailActions(open: {}, preview: { _ in nil }, observeTarget: { _, frame, center in
            if abs(frame.midX - center.x) < 0.5 && abs(frame.midY - center.y) < 0.5 && frame.width > 10 { observations += 1 }
        })
        let host = UIHostingController(rootView: actions.frame(width: 160, height: 90))
        let scroll = UIScrollView(frame: root.view.bounds)
        scroll.contentInsetAdjustmentBehavior = .never
        scroll.contentSize = CGSize(width: root.view.bounds.width, height: 1800)
        root.view.addSubview(scroll)
        root.addChild(host); host.view.frame = CGRect(x: 45, y: 560, width: 160, height: 90)
        scroll.addSubview(host.view); host.didMove(toParent: root)
        scroll.contentOffset = CGPoint(x: 0, y: 300); host.view.layoutIfNeeded()
        func sources(_ view: UIView) -> [ThumbnailActions.SourceView] {
            (view as? ThumbnailActions.SourceView).map { [$0] } ?? view.subviews.flatMap(sources)
        }
        guard let source = sources(host.view).first,
              let interaction = source.interactions.first as? UIContextMenuInteraction,
              let delegate = interaction.delegate as? ThumbnailActions.Coordinator else { fatalError("Missing native source interaction") }
        let actual = source.convert(source.bounds, to: window)
        check(abs(actual.minX - 45) < 0.5 && abs(actual.minY - 260) < 0.5 && abs(actual.width - 160) < 0.5, "Geometry follows scroll offset rather than unscrolled row coordinates")
        let configuration = UIContextMenuConfiguration(identifier: "fixture" as NSString, previewProvider: nil, actionProvider: nil)
        let lift = delegate.contextMenuInteraction(interaction, configuration: configuration, highlightPreviewForItemWithIdentifier: "fixture" as NSString)
        let drop = delegate.contextMenuInteraction(interaction, configuration: configuration, dismissalPreviewForItemWithIdentifier: "fixture" as NSString)
        check(observations == 2 && lift?.view === source && drop?.view === source && lift?.parameters.visiblePath?.bounds == source.bounds, "Lift and return use actual scrolled source and rounded path")
        check(lift?.parameters.visiblePath?.contains(CGPoint(x: 0, y: 0)) == false && lift?.parameters.visiblePath?.contains(CGPoint(x: 80, y: 45)) == true, "Rounded source path excludes outer corners")
        let receipt: [String: Any] = ["passed": failures.isEmpty, "failures": failures, "source_target": true,
            "dismiss_before_handoff": true, "single_handoff": true, "teardown": true, "all_tags_wrap": true, "lifecycle_cancellation": true]
        let path = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("quicklook-test.json")
        try! JSONSerialization.data(withJSONObject: receipt).write(to: path)
        print("QUICKLOOK_CHECKS: \(failures.isEmpty ? "PASS" : failures.joined(separator: "; "))")
        exit(failures.isEmpty ? 0 : 1)
    }
}
