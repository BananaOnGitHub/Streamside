import SwiftUI
import UIKit

@MainActor
struct ThumbnailActions: UIViewRepresentable {
    var image: UIImage?
    var label = "Stream thumbnail"
    let open: () -> Void
    let preview: (UIView) -> ContextPreviewSession?
    // Fixture-only observations of source geometry; production leaves nil.
    var observeTarget: ((Bool, CGRect, CGPoint) -> Void)?

    final class SourceView: UIImageView {
        var activate: (() -> Void)?
        var removed: (() -> Void)?
        var previewActivate: (() -> Void)?
        @objc func accessibilityPreview(_ action: UIAccessibilityCustomAction) -> Bool { previewActivate?(); return true }
        override func accessibilityActivate() -> Bool { activate?(); return true }
        override func didMoveToWindow() {
            super.didMoveToWindow()
            if window == nil {
                DispatchQueue.main.async { [weak self] in
                    if self?.window == nil { self?.removed?() }
                }
            }
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
            guard session == nil, let root = source.window?.rootViewController,
                  let created = owner.preview(source) else { return }
            session = created
            let presenter = AnchoredPreviewController(content: created.controller, source: source,
                watch: { [weak self] in self?.finish(watch: true) },
                dismiss: { [weak self] in self?.finish(watch: false) }, observeTarget: owner.observeTarget)
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
        let view = SourceView()
        view.isUserInteractionEnabled = true; view.isAccessibilityElement = true
        view.accessibilityTraits = .button
        view.accessibilityHint = "Tap to watch. Touch and hold for a stream preview and actions."
        view.backgroundColor = .secondarySystemBackground
        view.contentMode = .scaleAspectFill; view.clipsToBounds = true
        view.layer.cornerRadius = 7; view.layer.cornerCurve = .continuous
        let hold = UILongPressGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.hold(_:)))
        hold.minimumPressDuration = 0.45; hold.allowableMovement = 10
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.tap(_:)))
        tap.require(toFail: hold)
        view.addGestureRecognizer(hold); view.addGestureRecognizer(tap)
        view.activate = { [weak coordinator = context.coordinator] in coordinator?.activate() }
        view.previewActivate = { [weak view, weak coordinator = context.coordinator] in
            if let view { coordinator?.preview(from: view) }
        }
        view.accessibilityCustomActions = [UIAccessibilityCustomAction(name: "Preview stream", target: view, selector: #selector(SourceView.accessibilityPreview(_:)))]
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
    static func dismantleUIView(_ view: SourceView, coordinator: Coordinator) { coordinator.removed() }
}
