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
            self.holdFeedback()
        }
    }
    func holdFeedback() {
        guard let window, let root = window.rootViewController else { fatalError("Missing fixture root") }
        let clip = UIView(frame: CGRect(x: 40, y: 200, width: 160, height: 90)); clip.clipsToBounds = true
        let source = ThumbnailActions.SourceView(frame: clip.bounds); source.backgroundColor = .systemIndigo
        root.view.addSubview(clip); clip.addSubview(source)
        let original = source.convert(source.bounds, to: window)
        // snapshotView captures already rendered content; admit a display turn.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) {
            source.beginPress(reduceMotion: false)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.28) {
                let lifted = source.takePressLift()
                self.check((lifted?.frame.width ?? 0) > 161 && (lifted?.frame.width ?? 999) <= 168.1, "Intermediate hold enlarges slightly and survives capture")
                self.check(abs((lifted?.frame.midX ?? 0) - original.midX) < 0.5 && abs((lifted?.frame.midY ?? 0) - original.midY) < 0.5, "Hold remains centered in place")
                self.check(!clip.bounds.contains(source.convert(lifted?.frame ?? .zero, from: window)), "Lift extends beyond clipping ancestor")
                self.check(source.transform == .identity && source.layer.opacity == 1, "Capture restores unchanged layout source")
                let content = QuickLookController(content: UIViewController(), size: CGSize(width: 370, height: 360))
                let preview = AnchoredPreviewController(content: content, source: source, watch: {}, dismiss: {}, observeTarget: nil, initialLift: lifted)
                self.check(preview.install(in: root) && lifted?.isDescendant(of: preview.view) == true, "Opening reuses the lifted object")
                preview.dismiss(watching: false) {
                    self.check(!source.isHidden && source.convert(source.bounds, to: window) == original, "Return preserves source geometry")
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) {
                        source.beginPress(reduceMotion: true)
                        self.check(source.takePressLift() == nil && source.layer.opacity == 1, "Reduce Motion skips preliminary enlargement")
                        source.beginPress(reduceMotion: false)
                        self.check(source.layer.opacity == 0, "Early-release test must first install a lift")
                        source.endPress()
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                            self.check(source.layer.opacity == 1 && source.takePressLift() == nil, "Early release removes passive lift and restores source")
                            source.beginPress(reduceMotion: false)
                            self.check(source.layer.opacity == 0, "Inactive test must first install a lift")
                            NotificationCenter.default.post(name: UIApplication.willResignActiveNotification, object: nil)
                            self.check(source.takePressLift() == nil && source.layer.opacity == 1, "Inactive app removes pending hold snapshot")
                            clip.removeFromSuperview(); self.scrollReturn()
                        }
                    }
                }
            }
        }
    }
    func scrollReturn() {
        guard let window, let root = window.rootViewController else { fatalError("Missing fixture root") }
        let scroll = UIScrollView(frame: root.view.bounds); scroll.contentInsetAdjustmentBehavior = .never
        scroll.contentSize = CGSize(width: window.bounds.width, height: 1800); root.view.addSubview(scroll)
        let source = ThumbnailActions.SourceView(frame: CGRect(x: 40, y: 400, width: 160, height: 90))
        source.backgroundColor = .systemIndigo; scroll.addSubview(source)
        var snapshot: UIView?
        source.observeHold = { snapshot = $0 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) {
            source.beginPress(reduceMotion: false)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.28) {
                let before = snapshot?.layer.presentation().map { $0.convert($0.bounds, to: window.layer).width } ?? 0
                source.endPress(); source.endPress() // Gesture failure plus reset must keep the return alive.
                self.check(snapshot?.window === window && source.layer.opacity == 0, "Scroll cancellation retains the visible snapshot")
                scroll.contentOffset = CGPoint(x: 0, y: 40)
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                    let shown = snapshot?.frame ?? .zero, target = source.convert(source.bounds, to: window)
                    self.check(shown.width > 160 && shown.width < before, "Scroll cancellation visibly shrinks over intermediate frames")
                    self.check(abs(shown.midY - target.midY) < 1, "Return follows the moving row")
                    scroll.contentOffset = CGPoint(x: 0, y: 100)
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                        self.check(snapshot?.window == nil && source.layer.opacity == 1, "Moving-source return cleans up and restores thumbnail")
                        source.observeHold = nil; snapshot = nil; scroll.removeFromSuperview(); self.sourceTarget()
                    }
                }
            }
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
        check(content.view.accessibilityIdentifier == "quicklook.bounds" && !content.view.isAccessibilityElement,
            "Clip boundary remains an identified container without hiding preview accessibility children")
        check(preview.parent === root && root.presentedViewController == nil && source.isHidden, "Child ownership preserves root and lifts source")
        preview.dismiss(watching: false) {
            self.check(preview.parent == nil && !source.isHidden && targets == [false, true], "Interrupted lift restores source and detaches once")
            self.interactiveReturn()
        }
    }
    func interactiveReturn() {
        guard let window, let root = window.rootViewController else { fatalError("Missing fixture root") }
        let scroll = UIScrollView(frame: root.view.bounds)
        scroll.contentInsetAdjustmentBehavior = .never
        scroll.contentSize = CGSize(width: window.bounds.width, height: 2000); root.view.addSubview(scroll)
        let source = ThumbnailActions.SourceView(frame: CGRect(x: 45, y: 300, width: 160, height: 90))
        source.backgroundColor = .systemIndigo; scroll.addSubview(source)
        let button = UIButton(frame: CGRect(x: 230, y: 700, width: 100, height: 50)); scroll.addSubview(button)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) {
            let snapshot = source.snapshotView(afterScreenUpdates: false)
            self.check(snapshot != nil, "Return test requires actual source artwork")
            let content = QuickLookController(content: UIViewController(), size: CGSize(width: 370, height: 360))
            let preview = AnchoredPreviewController(content: content, source: source, watch: {}, dismiss: {}, observeTarget: nil, initialLift: snapshot)
            self.check(preview.install(in: root), "Install interactive-return fixture")
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.55) {
                let started = CACurrentMediaTime()
                preview.dismiss(watching: false) {
                    let elapsed = CACurrentMediaTime() - started
                    self.check(elapsed >= 0.45 && elapsed < 0.85, "Scrolling never extends the existing 0.52s return deadline")
                    self.check(preview.parent == nil, "Returning overlay detaches at its deadline")
                    self.check(source.isHidden, "Old completion cannot unhide a source claimed by a newer preview")
                    source.isHidden = false; scroll.removeFromSuperview(); self.coordinatorRelease()
                }
                self.check(!preview.view.isUserInteractionEnabled && !preview.view.accessibilityViewIsModal && !source.isHidden,
                    "Dismissal immediately releases feed input and accessibility ownership")
                let hit = root.view.hitTest(button.convert(CGPoint(x: 50, y: 25), to: root.view), with: nil)
                self.check(hit === button, "Underlying feed control is hittable while return is visible")
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { scroll.contentOffset.y = 100 }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                    let shift = snapshot?.superview?.transform.ty ?? 0
                    self.check(shift < -60 && shift >= -101, "Visible return tracks the newly scrolled source")
                    // Simulate a subsequent preview owning this same source.
                    source.isHidden = true
                }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.42) { scroll.contentOffset.y = 170 }
            }
        }
    }
    func coordinatorRelease() {
        guard let root = window?.rootViewController else { fatalError("Missing fixture root") }
        let source = ThumbnailActions.SourceView(frame: CGRect(x: 45, y: 300, width: 160, height: 90))
        source.backgroundColor = .systemIndigo; root.view.addSubview(source)
        var latest: ContextPreviewSession?
        var opens = 0, starts = 0, stops = 0, releases = 0
        let owner = ThumbnailActions(image: nil, open: { opens += 1 }, preview: { _ in
            let content = QuickLookController(content: UIViewController(), size: CGSize(width: 370, height: 360))
            let session = ContextPreviewSession(controller: content, claim: { _ in true }, release: { _ in releases += 1 }, valid: { true },
                start: { starts += 1 }, stop: { stops += 1 }, handoff: { false })
            latest = session; return session
        })
        let coordinator = owner.makeCoordinator()
        coordinator.preview(from: source); latest?.cancel(); coordinator.activate()
        check(opens == 1 && stops == 1 && releases == 1, "Closing releases the row and media immediately")
        coordinator.preview(from: source)
        check(starts == 2 && latest?.phase == .visible, "New preview opens before old visual return finishes")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.65) {
            coordinator.activate()
            self.check(opens == 1 && latest?.phase == .visible, "Old completion cannot clear a newer session")
            latest?.cancel()
            self.check(stops == 2 && releases == 2, "Each cancelled session releases media exactly once")
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { source.removeFromSuperview(); self.authorizationFixture() }
        }
    }
    func authorizationFixture() {
        guard let root = window?.rootViewController else { fatalError("Missing fixture root") }
        let source = ThumbnailActions.SourceView(frame: CGRect(x: 45, y: 300, width: 160, height: 90))
        root.view.addSubview(source)
        var pending: ((Bool) -> Void)?
        var admissions = 0, allocations = 0, starts = 0
        var latest: ContextPreviewSession?
        let owner = ThumbnailActions(open: { self.check(false, "Tap cannot race pending consent") }, preview: { _ in
            allocations += 1
            let controller = QuickLookController(content: UIViewController(), size: CGSize(width: 370, height: 360))
            let session = ContextPreviewSession(controller: controller, claim: { _ in true }, release: { _ in }, valid: { true },
                start: { starts += 1 }, stop: {}, handoff: { false })
            latest = session; return session
        }, authorizePreview: { _, completion in admissions += 1; pending = completion })
        let coordinator = owner.makeCoordinator()
        coordinator.preview(from: source); coordinator.preview(from: source); coordinator.activate()
        check(admissions == 1 && allocations == 0 && starts == 0, "No player allocation or duplicate consent while waiting")
        pending?(false); check(allocations == 0, "Close never creates playback")
        coordinator.preview(from: source); pending?(true)
        check(admissions == 2 && allocations == 1 && starts == 1, "Approval creates and starts exactly one preview")
        latest?.cancel()
        coordinator.preview(from: source); coordinator.removed(); pending?(true)
        check(allocations == 1 && starts == 1, "Late approval after source cancellation cannot start media")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.65) { source.removeFromSuperview(); self.finishReceipt() }
    }
    func finishReceipt() {
        let receipt: [String: Any] = ["passed": failures.isEmpty, "failures": failures, "source_target": true, "hold_cancellation": true, "unblocked_return": true,
            "dismiss_before_handoff": true, "single_handoff": true, "teardown": true, "all_tags_wrap": true, "lifecycle_cancellation": true, "consent_before_preview": true]
        let path = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("quicklook-test.json")
        try! JSONSerialization.data(withJSONObject: receipt).write(to: path)
        print("QUICKLOOK_CHECKS: \(failures.isEmpty ? "PASS" : failures.joined(separator: "; "))")
        exit(failures.isEmpty ? 0 : 1)
    }
}
