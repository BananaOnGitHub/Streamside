import SwiftUI
import UIKit

// TextKit supplies link-specific hit-testing, wrapping, and native context
// menus while SwiftUI still owns the surrounding Markdown block layout.
@available(iOS 17.0, *)
struct PanelMarkdownLinkText: UIViewRepresentable {
    let text: AttributedString
    let style: UIFont.TextStyle
    let bold: Bool
    let accent: Color
    let previewSize: CGSize
    @Environment(\.openURL) private var openURL
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    struct RenderedText: Equatable {
        let text: AttributedString
        let style: UIFont.TextStyle
        let bold: Bool
        let dynamicTypeSize: DynamicTypeSize
    }

    final class Coordinator: NSObject, UITextViewDelegate {
        let linkMenu = PanelLinkMenu()
        var renderedText: RenderedText?

        func textView(_ textView: UITextView, primaryActionFor textItem: UITextItem, defaultAction: UIAction) -> UIAction? {
            guard case .link(let url) = textItem.content else { return defaultAction }
            return UIAction(title: "Open link") { [weak self] _ in self?.linkMenu.open(url) }
        }

        func textView(_ textView: UITextView, menuConfigurationFor textItem: UITextItem,
                      defaultMenu: UIMenu) -> UITextItem.MenuConfiguration? {
            // The shared interaction handles link holds and preview commits.
            if case .link = textItem.content { return nil }
            return .init(preview: nil, menu: defaultMenu)
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> UITextView {
        let view = UITextView()
        view.delegate = context.coordinator
        let menu = context.coordinator.linkMenu
        menu.destination = { [weak view] point in
            guard let view, let range = view.characterRange(at: point),
                  view.firstRect(for: range).contains(point) else { return nil }
            let index = view.offset(from: view.beginningOfDocument, to: range.start)
            guard let text = view.attributedText, index >= 0, index < text.length else { return nil }
            return text.attribute(.link, at: index, effectiveRange: nil) as? URL
        }
        view.addInteraction(UIContextMenuInteraction(delegate: menu))
        view.isEditable = false
        view.isSelectable = true
        view.isScrollEnabled = false
        view.backgroundColor = .clear
        view.textContainerInset = .zero
        view.textContainer.lineFragmentPadding = 0
        view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        view.accessibilityIdentifier = "profile.markdown-link-text"
        return view
    }

    func updateUIView(_ view: UITextView, context: Context) {
        let openURL = openURL
        context.coordinator.linkMenu.open = { url in openURL(url) }
        context.coordinator.linkMenu.previewSize = previewSize
        view.linkTextAttributes = [.foregroundColor: UIColor(accent), .underlineStyle: NSUnderlineStyle.single.rawValue]
        let input = RenderedText(text: text, style: style, bold: bold, dynamicTypeSize: dynamicTypeSize)
        guard context.coordinator.renderedText != input else { return }
        context.coordinator.renderedText = input
        let trait = UITraitCollection(preferredContentSizeCategory: UIContentSizeCategory(dynamicTypeSize))
        let base = UIFont.preferredFont(forTextStyle: style, compatibleWith: trait)
        let content = NSMutableAttributedString(string: "")
        for run in text.runs {
            let intent = run.inlinePresentationIntent ?? []
            var font = intent.contains(.code) ? UIFont.monospacedSystemFont(ofSize: base.pointSize, weight: .regular) : base
            var traits = font.fontDescriptor.symbolicTraits
            if bold || intent.contains(.stronglyEmphasized) { traits.insert(.traitBold) }
            if intent.contains(.emphasized) { traits.insert(.traitItalic) }
            if let descriptor = font.fontDescriptor.withSymbolicTraits(traits) {
                font = UIFont(descriptor: descriptor, size: font.pointSize)
            }
            var attributes: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: UIColor.label]
            if intent.contains(.strikethrough) { attributes[.strikethroughStyle] = NSUnderlineStyle.single.rawValue }
            if let url = run.link { attributes[.link] = url }
            content.append(NSAttributedString(string: String(text[run.range].characters), attributes: attributes))
        }
        if view.attributedText != content { view.attributedText = content }
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UITextView, context: Context) -> CGSize? {
        let width = proposal.width ?? ceil(uiView.attributedText?.size().width ?? 0)
        guard width.isFinite, width > 0 else { return nil }
        return CGSize(width: width, height: ceil(uiView.sizeThatFits(CGSize(width: width, height: .greatestFiniteMagnitude)).height))
    }
}
