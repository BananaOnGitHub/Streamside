import SwiftUI
import UIKit
import UIKit.UIGestureRecognizerSubclass

@MainActor
struct ThumbnailActions: UIViewRepresentable {
    var image: UIImage?
    var label = "Stream thumbnail"
    let open: () -> Void
    let preview: (UIView) -> ContextPreviewSession?
    // Fixture-only observations of source geometry; production leaves nil.
    var observeTarget: ((Bool, CGRect, CGPoint) -> Void)?
    var observeHold: ((UIView) -> Void)?

    final class SourceView: UIImageView {
        var activate: (() -> Void)?
        var removed: (() -> Void)?
        var previewActivate: (() -> Void)?
        var observeHold: ((UIView) -> Void)?
        private var pressAnimator: UIViewPropertyAnimator?
        private var pressLift: UIView?
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
            // A slow outward pull throughout the possible phase, without a
            // spring bounce or an inward press. Recognition continues this view.
            let target = PreviewPlacement.holdTarget(viewport: PreviewPlacement.viewport(in: window), source: frame)
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
            guard pressing, let lift = pressLift, let window, lift.window === window,
                  !UIAccessibility.isReduceMotionEnabled else { resetPress(); return }
            pressing = false; freezeLift(lift)
            let target = convert(bounds, to: window)
            let animator = UIViewPropertyAnimator(duration: 0.22, dampingRatio: 1) { lift.frame = target }
            animator.addCompletion { [weak self, weak lift] _ in
                guard let self, let lift, self.pressLift === lift else { return }
                self.resetPress()
            }
            pressAnimator = animator; animator.startAnimation()
        }
        private func freezeLift(_ lift: UIView) {
            let frame = lift.layer.presentation().map { $0.convert($0.bounds, to: lift.superview?.layer) } ?? lift.frame
            stopPressAnimation(); lift.frame = frame
        }
        private func stopPressAnimation() {
            if let animator = pressAnimator, animator.state == .active { animator.stopAnimation(true) }
            pressAnimator = nil
        }
        @objc func resetPress() {
            pressing = false; stopPressAnimation()
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
            if state == .failed || state == .cancelled { (view as? SourceView)?.resetPress() }
        }
        override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent) {
            super.touchesEnded(touches, with: event); (view as? SourceView)?.endPress()
        }
        override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent) {
            super.touchesCancelled(touches, with: event); (view as? SourceView)?.resetPress()
        }
        override func reset() {
            (view as? SourceView)?.endPress(); super.reset()
        }
    }
    @MainActor final class Coordinator: NSObject {
        var owner: ThumbnailActions
        private var session: ContextPreviewSession?
        private var presenter: AnchoredPreviewController?
        init(_ owner: ThumbnailActions) { self.owner = owner }
        @objc func tap(_ gesture: UITapGestureRecognizer) {
            guard gesture.state == .ended, session == nil else { return }
            (gesture.view as? SourceView)?.resetPress(); owner.open()
        }
        func activate() { if session == nil { owner.open() } }
        @objc func hold(_ gesture: UILongPressGestureRecognizer) {
            guard gesture.state == .began, let source = gesture.view else { return }
            preview(from: source)
        }
        func preview(from source: UIView) {
            let lift = (source as? SourceView)?.takePressLift()
            guard session == nil, let root = source.window?.rootViewController,
                  let created = owner.preview(source) else { return }
            session = created
            let presenter = AnchoredPreviewController(content: created.controller, source: source,
                watch: { [weak self] in self?.finish(watch: true) },
                dismiss: { [weak self] in self?.finish(watch: false) }, observeTarget: owner.observeTarget,
                initialLift: lift)
            self.presenter = presenter
            created.dismissPreview = { [weak self, weak presenter, weak created] in
                presenter?.dismiss(watching: false) { [weak self, weak created] in self?.clear(created) }
            }
            guard created.display(), presenter.install(in: root) else { created.cancel(); clear(created); return }
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
        }
        private func finish(watch: Bool) {
            guard let session, session.phase == .visible, let presenter else { return }
            if watch { session.requestWatch() }
            session.end(after: { complete in
                presenter.dismiss(watching: watch) { [weak self, weak session] in self?.clear(session); complete() }
            })
        }
        private func clear(_ ended: ContextPreviewSession?) {
            if session === ended { presenter = nil; session = nil }
        }
        func removed() { session?.cancel() }
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
