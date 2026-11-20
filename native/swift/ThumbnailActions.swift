import SwiftUI
import UIKit
import UIKit.UIGestureRecognizerSubclass

@MainActor
struct ThumbnailActions: UIViewRepresentable {
    var image: UIImage?
    var label = "Stream thumbnail"
    let open: () -> Void
    let preview: (UIView) -> ContextPreviewSession?
    var authorizePreview: ((UIView, @escaping (Bool) -> Void) -> Void)?
    // Fixture-only observations of source geometry; production leaves nil.
    var observeTarget: ((Bool, CGRect, CGPoint) -> Void)?
    var observeHold: ((UIView) -> Void)?
    var observeReturnCompletion: (() -> Void)?

    final class SourceView: UIImageView {
        var activate: (() -> Void)?
        var removed: (() -> Void)?
        var previewActivate: (() -> Void)?
        var observeHold: ((UIView) -> Void)?
        private var pressAnimator: UIViewPropertyAnimator?
        private var pressLift: UIView?
        private var returnLink: CADisplayLink?
        private struct ReturnMotion {
            let started: CFTimeInterval
            let scale: CGSize
            let offset: CGPoint
        }
        private var returnMotion: ReturnMotion?
        private var sourceOpacity: Float = 1
        private var pressing = false
        override init(frame: CGRect) {
            super.init(frame: frame)
            NotificationCenter.default.addObserver(self, selector: #selector(resetPress),
                name: UIApplication.willResignActiveNotification, object: nil)
        }
        required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
        // Keep feedback outside SwiftUI's thumbnail/row clips. This is a passive
        // child of the existing window, never another window or a media request.
        func beginPress() { beginPress(reduceMotion: UIAccessibility.isReduceMotionEnabled) }
        func beginPress(reduceMotion: Bool) {
            guard !pressing, let window, !isHidden else { return }
            resetPress(); pressing = true
            guard !reduceMotion, let lift = snapshotView(afterScreenUpdates: false) else { return }
            let frame = convert(bounds, to: window)
            lift.frame = frame; lift.isUserInteractionEnabled = false; lift.accessibilityElementsHidden = true
            lift.layer.cornerRadius = 7; lift.layer.cornerCurve = .continuous; lift.layer.masksToBounds = true
            window.addSubview(lift); pressLift = lift
            sourceOpacity = layer.opacity; layer.opacity = 0
            observeHold?(lift)
            // Slight expansion in place. Recognition continues this snapshot;
            // it only travels toward the larger card after preview admission.
            let target = PreviewPlacement.holdTarget(source: frame)
            let animator = UIViewPropertyAnimator(duration: 0.4, curve: .easeIn) { lift.frame = target }
            pressAnimator = animator; animator.startAnimation(afterDelay: 0.05)
        }
        // Freeze the actual onscreen snapshot and transfer that same object to
        // the presenter. Do not recreate it from the clipped layout source.
        func takePressLift() -> UIView? {
            guard let lift = pressLift else { resetPress(); return nil }
            freezeLift(lift); pressLift = nil; pressing = false
            layer.opacity = sourceOpacity; lift.removeFromSuperview(); return lift
        }
        func endPress() {
            // UIKit may deliver failure, cancellation and reset for one scroll.
            // Once returning, repeated callbacks must not remove the animation.
            guard pressing else { return }
            guard let lift = pressLift, let window, lift.window === window,
                  !UIAccessibility.isReduceMotionEnabled else { resetPress(); return }
            pressing = false; freezeLift(lift)
            let target = convert(bounds, to: window)
            returnMotion = ReturnMotion(started: CACurrentMediaTime(),
                scale: CGSize(width: lift.frame.width / max(1, target.width), height: lift.frame.height / max(1, target.height)),
                offset: CGPoint(x: lift.frame.midX - target.midX, y: lift.frame.midY - target.midY))
            let link = CADisplayLink(target: self, selector: #selector(stepReturn(_:)))
            returnLink = link; link.add(to: .main, forMode: .common)
        }
        @objc private func stepReturn(_ link: CADisplayLink) {
            guard let motion = returnMotion, let lift = pressLift, let window, lift.window === window else { resetPress(); return }
            let progress = min(1, max(0, CGFloat((link.timestamp - motion.started) / 0.24)))
            let remaining = (1 - progress) * (1 - progress) * (1 - progress)
            // Track the actual row as the scroll view moves, while shrinking
            // smoothly to it. A fixed window endpoint would trail the feed.
            let target = convert(bounds, to: window)
            let width = target.width * (1 + (motion.scale.width - 1) * remaining)
            let height = target.height * (1 + (motion.scale.height - 1) * remaining)
            lift.frame = CGRect(x: target.midX + motion.offset.x * remaining - width / 2,
                y: target.midY + motion.offset.y * remaining - height / 2, width: width, height: height)
            if progress >= 1 { resetPress() }
        }
        private func stopReturn() { returnLink?.invalidate(); returnLink = nil; returnMotion = nil }
        private func freezeLift(_ lift: UIView) {
            let frame = lift.layer.presentation().map { $0.convert($0.bounds, to: lift.superview?.layer) } ?? lift.frame
            stopReturn(); stopPressAnimation(); lift.frame = frame
        }
        private func stopPressAnimation() {
            if let animator = pressAnimator, animator.state == .active { animator.stopAnimation(true) }
            pressAnimator = nil
        }
        @objc func resetPress() {
            pressing = false; stopReturn(); stopPressAnimation()
            if let lift = pressLift { lift.removeFromSuperview(); pressLift = nil; layer.opacity = sourceOpacity }
        }
        @objc func accessibilityPreview(_ action: UIAccessibilityCustomAction) -> Bool { previewActivate?(); return true }
        override func accessibilityActivate() -> Bool { activate?(); return true }
        override func didMoveToWindow() {
            super.didMoveToWindow()
            if window == nil {
                resetPress()
                DispatchQueue.main.async { [weak self] in
                    if self?.window == nil { self?.removed?() }
                }
            }
        }
    }
    // Observe the existing recognizer's possible phase without introducing a
    // competing recognizer. UIKit still owns hold duration and scroll failure.
    final class HoldGesture: UILongPressGestureRecognizer {
        override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
            super.touchesBegan(touches, with: event)
            if state == .possible { (view as? SourceView)?.beginPress() }
        }
        override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent) {
            super.touchesMoved(touches, with: event)
            if state == .failed || state == .cancelled { (view as? SourceView)?.endPress() }
        }
        override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent) {
            super.touchesEnded(touches, with: event); (view as? SourceView)?.endPress()
        }
        override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent) {
            super.touchesCancelled(touches, with: event); (view as? SourceView)?.endPress()
        }
        override func reset() {
            (view as? SourceView)?.endPress(); super.reset()
        }
    }
    @MainActor final class Coordinator: NSObject {
        var owner: ThumbnailActions
        private var session: ContextPreviewSession?
        private var presenter: AnchoredPreviewController?
        private var authorizationID: UUID?
        init(_ owner: ThumbnailActions) { self.owner = owner }
        @objc func tap(_ gesture: UITapGestureRecognizer) {
            guard gesture.state == .ended, session == nil, authorizationID == nil else { return }
            (gesture.view as? SourceView)?.resetPress(); owner.open()
        }
        func activate() { if session == nil && authorizationID == nil { owner.open() } }
        @objc func hold(_ gesture: UILongPressGestureRecognizer) {
            guard gesture.state == .began, let source = gesture.view else { return }
            preview(from: source)
        }
        func preview(from source: UIView) {
            guard session == nil, authorizationID == nil else { return }
            guard let authorize = owner.authorizePreview else { showPreview(from: source); return }
            let ticket = UUID(); authorizationID = ticket
            authorize(source) { [weak self, weak source] accepted in
                guard let self, self.authorizationID == ticket else { return }
                self.authorizationID = nil
                guard accepted, let source, source.window != nil else { return }
                self.showPreview(from: source)
            }
            // A delayed content warning owns the interaction; don't leave the
            // passive press snapshot floating above it. Normal holds stay intact.
            if authorizationID != nil { (source as? SourceView)?.resetPress() }
        }
        private func showPreview(from source: UIView) {
            let lift = (source as? SourceView)?.takePressLift()
            guard session == nil, let root = source.window?.rootViewController,
                  let created = owner.preview(source) else { return }
            session = created
            let presenter = AnchoredPreviewController(content: created.controller, source: source,
                watch: { [weak self] in self?.finish(watch: true) },
                dismiss: { [weak self] in self?.finish(watch: false) }, observeTarget: owner.observeTarget,
                initialLift: lift, videoTapAvailability: created.videoTapAvailability,
                profile: created.canViewProfile ? { [weak self] in self?.finishProfile() } : nil)
            self.presenter = presenter
            created.activateProfile = { [weak self] in self?.finishProfile() }
            let returned = owner.observeReturnCompletion
            created.dismissPreview = { [weak self, weak presenter, weak created] in
                guard let presenter else { self?.clear(created); return }
                // Release input/media ownership before the passive return.
                // Old completion must not clear a newer preview on this row.
                self?.clear(created)
                presenter.dismiss(watching: false) { returned?() }
            }
            guard created.display(), presenter.install(in: root) else { created.cancel(); clear(created); return }
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
        }
        private func finish(watch: Bool) {
            guard let session, session.phase == .visible, let presenter else { return }
            if !watch { session.cancel(); return }
            session.requestWatch()
            session.end(after: { complete in
                presenter.dismiss(watching: watch) { [weak self, weak session] in self?.clear(session); complete() }
            })
        }
        private func finishProfile() {
            guard let session, session.phase == .visible, session.canViewProfile, let presenter else { return }
            session.requestProfile()
            session.end(after: { complete in
                presenter.dismiss(watching: true) { [weak self, weak session] in self?.clear(session); complete() }
            })
        }
        private func clear(_ ended: ContextPreviewSession?) {
            if session === ended { presenter = nil; session = nil }
        }
        func removed() { authorizationID = nil; session?.cancel() }
    }
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeUIView(context: Context) -> SourceView {
        let view = SourceView(frame: .zero)
        view.isUserInteractionEnabled = true; view.isAccessibilityElement = true
        view.accessibilityTraits = .button
        view.accessibilityHint = "Tap to watch. Touch and hold for a stream preview and actions."
        view.backgroundColor = .secondarySystemBackground
        view.contentMode = .scaleAspectFill; view.clipsToBounds = true
        view.layer.cornerRadius = 7; view.layer.cornerCurve = .continuous
        let hold = HoldGesture(target: context.coordinator, action: #selector(Coordinator.hold(_:)))
        hold.minimumPressDuration = 0.45; hold.allowableMovement = 10
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.tap(_:)))
        tap.require(toFail: hold)
        view.addGestureRecognizer(hold); view.addGestureRecognizer(tap)
        view.activate = { [weak coordinator = context.coordinator] in coordinator?.activate() }
        view.previewActivate = { [weak view, weak coordinator = context.coordinator] in
            if let view { coordinator?.preview(from: view) }
        }
        view.accessibilityCustomActions = [UIAccessibilityCustomAction(name: "Preview stream", target: view, selector: #selector(SourceView.accessibilityPreview(_:)))]
        view.observeHold = { [weak coordinator = context.coordinator] source in coordinator?.owner.observeHold?(source) }
        view.removed = { [weak coordinator = context.coordinator] in coordinator?.removed() }
        return view
    }
    func updateUIView(_ view: SourceView, context: Context) {
        context.coordinator.owner = self
        view.image = image
        view.accessibilityLabel = label
    }
    func sizeThatFits(_ proposal: ProposedViewSize, uiView: SourceView, context: Context) -> CGSize? {
        guard let width = proposal.width, let height = proposal.height else { return nil }
        return CGSize(width: width, height: height)
    }
    static func dismantleUIView(_ view: SourceView, coordinator: Coordinator) { view.resetPress(); coordinator.removed() }
}
