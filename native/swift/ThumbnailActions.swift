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
        private var pressing = false
        override init(frame: CGRect) {
            super.init(frame: frame)
            NotificationCenter.default.addObserver(self, selector: #selector(resetPress),
                name: UIApplication.willResignActiveNotification, object: nil)
        }
        required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
        // Feedback while the long press is still possible; this never recognizes
        // a gesture, claims playback, or delays the containing scroll view.
        func beginPress() { beginPress(reduceMotion: UIAccessibility.isReduceMotionEnabled) }
        func beginPress(reduceMotion: Bool) {
            guard !pressing, window != nil, !isHidden else { return }
            resetPress(); pressing = true; observeHold?(self)
            guard !reduceMotion else { return }
            let animator = UIViewPropertyAnimator(duration: 0.34, dampingRatio: 1) {
                self.transform = CGAffineTransform(scaleX: 1.045, y: 1.045)
            }
            pressAnimator = animator; animator.startAnimation(afterDelay: 0.06)
        }
        // Return the displayed rectangle before resetting the layout view. The
        // preview snapshot starts here, so recognition does not snap back first.
        func takePressFrame() -> CGRect? {
            let frame = window.map { window in
                let shown = layer.presentation() ?? layer
                return shown.convert(shown.bounds, to: window.layer)
            }
            resetPress(); return frame
        }
        func endPress() {
            guard pressing else { return }
            pressing = false
            let shown = layer.presentation().map { CATransform3DGetAffineTransform($0.transform) } ?? transform
            stopPressAnimation()
            transform = shown
            guard !UIAccessibility.isReduceMotionEnabled, window != nil else { transform = .identity; return }
            let animator = UIViewPropertyAnimator(duration: 0.3, dampingRatio: 1) { self.transform = .identity }
            pressAnimator = animator; animator.startAnimation()
        }
        private func stopPressAnimation() {
            if let animator = pressAnimator, animator.state == .active { animator.stopAnimation(true) }
            pressAnimator = nil
        }
        @objc func resetPress() {
            pressing = false; stopPressAnimation(); transform = .identity
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
        init(_ owner: ThumbnailActions) { self.owner = owner }
        @objc func tap(_ gesture: UITapGestureRecognizer) {
            guard gesture.state == .ended, session == nil else { return }
            owner.open()
        }
        func activate() { if session == nil { owner.open() } }
        @objc func hold(_ gesture: UILongPressGestureRecognizer) {
            guard gesture.state == .began, let source = gesture.view else { return }
            preview(from: source)
        }
        func preview(from source: UIView) {
            let liftedFrame = (source as? SourceView)?.takePressFrame()
            guard session == nil, let root = source.window?.rootViewController,
                  let created = owner.preview(source) else { return }
            session = created
            let presenter = AnchoredPreviewController(content: created.controller, source: source,
                watch: { [weak self] in self?.finish(watch: true) },
                dismiss: { [weak self] in self?.finish(watch: false) }, observeTarget: owner.observeTarget,
                initialLiftFrame: liftedFrame)
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
