import SwiftUI
import UIKit

struct ThumbnailActions: UIViewRepresentable {
    var image: UIImage?
    var label = "Stream thumbnail"
    let open: () -> Void
    let preview: (UIView) -> ContextPreviewSession?
    // Fixture-only observations of public target geometry; production leaves nil.
    var observeTarget: ((Bool, CGRect, CGPoint) -> Void)?

    final class SourceView: UIImageView {
        var activate: (() -> Void)?
        var removed: (() -> Void)?
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
    final class Coordinator: NSObject, UIContextMenuInteractionDelegate {
        var owner: ThumbnailActions
        private var session: ContextPreviewSession?
        init(_ owner: ThumbnailActions) { self.owner = owner }
        @objc func tap(_ gesture: UITapGestureRecognizer) {
            guard gesture.state == .ended, session == nil else { return }
            owner.open()
        }
        func removed() { session?.cancel(); session = nil }
        func contextMenuInteraction(_ interaction: UIContextMenuInteraction, configurationForMenuAtLocation location: CGPoint) -> UIContextMenuConfiguration? {
            guard session == nil, let source = interaction.view, source.window != nil,
                  let created = owner.preview(source) else { return nil }
            session = created
            created.dismissMenu = { [weak interaction] in interaction?.dismissMenu() }
            let configuration = UIContextMenuConfiguration(identifier: created.id.uuidString as NSString, previewProvider: { created.controller }) { _ in
                let watch = UIAction(title: "Watch stream", image: UIImage(systemName: "play.fill")) { [weak created] _ in created?.requestWatch() }
                let profile = UIAction(title: "View profile", image: UIImage(systemName: "person.fill"), attributes: .disabled) { _ in }
                return UIMenu(children: [watch, profile])
            }
            configuration.preferredMenuElementOrder = .fixed
            return configuration
        }
        func contextMenuInteraction(_ interaction: UIContextMenuInteraction, willDisplayMenuFor configuration: UIContextMenuConfiguration, animator: UIContextMenuInteractionAnimating?) {
            if session?.display() != true { interaction.dismissMenu() }
        }
        func contextMenuInteraction(_ interaction: UIContextMenuInteraction, willEndFor configuration: UIContextMenuConfiguration, animator: UIContextMenuInteractionAnimating?) {
            guard let ending = session else { return }
            ending.end(animator: animator)
            let clear = { [weak self, weak ending] in
                if self?.session === ending { self?.session = nil }
            }
            if let animator { animator.addCompletion(clear) } else { DispatchQueue.main.async(execute: clear) }
        }
        func contextMenuInteraction(_ interaction: UIContextMenuInteraction, willPerformPreviewActionForMenuWith configuration: UIContextMenuConfiguration, animator: UIContextMenuInteractionCommitAnimating) {
            animator.preferredCommitStyle = .dismiss
            session?.requestWatch()
            session?.end(animator: animator)
        }
        func contextMenuInteraction(_ interaction: UIContextMenuInteraction, configuration: UIContextMenuConfiguration, highlightPreviewForItemWithIdentifier identifier: NSCopying) -> UITargetedPreview? {
            target(interaction, dismissing: false)
        }
        func contextMenuInteraction(_ interaction: UIContextMenuInteraction, configuration: UIContextMenuConfiguration, dismissalPreviewForItemWithIdentifier identifier: NSCopying) -> UITargetedPreview? {
            target(interaction, dismissing: true)
        }
        private func target(_ interaction: UIContextMenuInteraction, dismissing: Bool) -> UITargetedPreview? {
            guard let source = interaction.view, let window = source.window else { return nil }
            let parameters = UIPreviewParameters()
            parameters.backgroundColor = .clear
            parameters.visiblePath = UIBezierPath(roundedRect: source.bounds, cornerRadius: 7)
            parameters.shadowPath = parameters.visiblePath
            let preview = UITargetedPreview(view: source, parameters: parameters)
            let target = preview.target.container.convert(preview.target.center, to: window)
            owner.observeTarget?(dismissing, source.convert(source.bounds, to: window), target)
            return preview
        }
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
        view.addInteraction(UIContextMenuInteraction(delegate: context.coordinator))
        view.addGestureRecognizer(UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.tap(_:))))
        view.activate = { [weak coordinator = context.coordinator] in coordinator?.owner.open() }
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
