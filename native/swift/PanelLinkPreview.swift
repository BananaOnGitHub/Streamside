import SwiftUI
import UIKit
import WebKit

// Panel images, inline Markdown and social links share the system commit
// callback. A tap on the preview opens the original destination.
@MainActor final class PanelLinkMenu: NSObject, UIContextMenuInteractionDelegate {
    var destination: (CGPoint) -> URL? = { _ in nil }
    var open: (URL) -> Void = { _ in }
    var previewSize = CGSize.zero
    var sourcePreview: ((CGPoint) -> UITargetedPreview?)?
    private weak var webView: WKWebView?

    private final class Link: NSObject, NSCopying {
        let url: URL
        let location: CGPoint

        init(url: URL, location: CGPoint) {
            self.url = url
            self.location = location
        }

        nonisolated func copy(with zone: NSZone? = nil) -> Any { self }
    }

    func contextMenuInteraction(_ interaction: UIContextMenuInteraction,
                                configurationForMenuAtLocation location: CGPoint) -> UIContextMenuConfiguration? {
        guard let url = destination(location) else { return nil }
        return UIContextMenuConfiguration(identifier: Link(url: url, location: location), previewProvider: { [weak self] in
            guard let self else { return nil }
            let configuration = WKWebViewConfiguration()
            configuration.websiteDataStore = .nonPersistent()
            configuration.defaultWebpagePreferences.allowsContentJavaScript = false
            configuration.mediaTypesRequiringUserActionForPlayback = .all
            let page = WKWebView(frame: CGRect(origin: .zero, size: self.previewSize), configuration: configuration)
            page.isUserInteractionEnabled = false
            page.accessibilityIdentifier = "profile.link-preview"
            page.load(URLRequest(url: url, timeoutInterval: 12))
            self.webView = page
            let controller = UIViewController()
            controller.view = page
            controller.preferredContentSize = self.previewSize
            return controller
        }, actionProvider: { [weak self] _ in
            UIMenu(children: [UIAction(title: "Open link", image: UIImage(systemName: "arrow.up.right")) { _ in
                self?.open(url)
            }])
        })
    }

    func contextMenuInteraction(_ interaction: UIContextMenuInteraction, configuration: UIContextMenuConfiguration,
                                highlightPreviewForItemWithIdentifier identifier: any NSCopying) -> UITargetedPreview? {
        targetedPreview(configuration)
    }

    func contextMenuInteraction(_ interaction: UIContextMenuInteraction, configuration: UIContextMenuConfiguration,
                                dismissalPreviewForItemWithIdentifier identifier: any NSCopying) -> UITargetedPreview? {
        targetedPreview(configuration)
    }

    private func targetedPreview(_ configuration: UIContextMenuConfiguration) -> UITargetedPreview? {
        guard let link = configuration.identifier as? Link else { return nil }
        return sourcePreview?(link.location)
    }

    func contextMenuInteraction(_ interaction: UIContextMenuInteraction,
                                willPerformPreviewActionForMenuWith configuration: UIContextMenuConfiguration,
                                animator: any UIContextMenuInteractionCommitAnimating) {
        guard let link = configuration.identifier as? Link else { return }
        let open = open
        animator.preferredCommitStyle = .dismiss
        animator.addCompletion { open(link.url) }
    }

    func contextMenuInteraction(_ interaction: UIContextMenuInteraction,
                                willEndFor configuration: UIContextMenuConfiguration,
                                animator: (any UIContextMenuInteractionAnimating)?) {
        webView?.stopLoading()
        webView = nil
    }
}

struct LinkedPanelImage: UIViewRepresentable {
    let image: UIImage
    let url: URL
    let title: String
    let previewSize: CGSize
    @Environment(\.openURL) private var openURL

    func makeCoordinator() -> PanelLinkMenu { PanelLinkMenu() }

    func makeUIView(context: Context) -> UIButton {
        let button = UIButton(type: .custom)
        button.clipsToBounds = true
        button.layer.cornerRadius = 12
        button.layer.cornerCurve = .continuous
        let menu = context.coordinator
        button.addInteraction(UIContextMenuInteraction(delegate: menu))
        button.addAction(UIAction(title: "Open link") { [weak menu] _ in
            guard let url = menu?.destination(.zero) else { return }
            menu?.open(url)
        }, for: .touchUpInside)
        button.isAccessibilityElement = true
        button.accessibilityTraits = [.link, .image]
        button.accessibilityIdentifier = "profile.panel-image-link"
        return button
    }

    func updateUIView(_ button: UIButton, context: Context) {
        let destination = url
        let openURL = openURL
        context.coordinator.destination = { _ in destination }
        context.coordinator.open = { openURL($0) }
        context.coordinator.previewSize = previewSize
        button.setBackgroundImage(image, for: .normal)
        button.accessibilityLabel = title.isEmpty ? "Open linked panel image" : "Open \(title)"
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UIButton, context: Context) -> CGSize? {
        let width = proposal.width ?? image.size.width
        guard width.isFinite, width >= 0 else { return nil }
        return CGSize(width: width, height: width * image.size.height / max(1, image.size.width))
    }

}
