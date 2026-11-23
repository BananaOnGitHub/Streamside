import SwiftUI
import UIKit

// TextKit owns text layout and selection. A sibling view receives touches
// on links so TextKit and the context menu never track the same link press.
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

    final class ContentView: UIView {
        let textView = UITextView()
        let linkTarget = LinkTarget()

        override init(frame: CGRect) {
            super.init(frame: frame)
            addSubview(textView)
            addSubview(linkTarget)
            linkTarget.textView = textView
        }

        required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }

        override func layoutSubviews() {
            super.layoutSubviews()
            textView.frame = bounds
            linkTarget.frame = bounds
        }
    }

    final class LinkTarget: UIView {
        weak var textView: UITextView?
        weak var menu: PanelLinkMenu?

        override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
            super.point(inside: point, with: event) && destination(at: point) != nil
        }

        func destination(at point: CGPoint) -> URL? {
            guard let view = textView, let text = view.attributedText else { return nil }
            let location = view.convert(point, from: self)
            guard let closest = view.closestPosition(to: location) else { return nil }
            let index = view.offset(from: view.beginningOfDocument, to: closest)
            // A caret in the last half of a glyph can fall at the insertion
            // point after a link. Check both neighbors against its line rects.
            for candidate in [index, index - 1] where (0..<text.length).contains(candidate) {
                var effective = NSRange()
                guard let url = text.attribute(.link, at: candidate, effectiveRange: &effective) as? URL,
                      let start = view.position(from: view.beginningOfDocument, offset: effective.location),
                      let end = view.position(from: start, offset: effective.length),
                      let range = view.textRange(from: start, to: end) else { continue }
                if view.selectionRects(for: range).contains(where: { $0.rect.insetBy(dx: -2, dy: -1).contains(location) }) {
                    return url
                }
            }
            return nil
        }

        @objc func openLink(_ gesture: UITapGestureRecognizer) {
            if let url = destination(at: gesture.location(in: self)) { menu?.open(url) }
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> ContentView {
        let content = ContentView(frame: .zero)
        let view = content.textView
        let linkTarget = content.linkTarget
        view.delegate = context.coordinator
        let menu = context.coordinator.linkMenu
        linkTarget.menu = menu
        menu.destination = { [weak linkTarget] point in linkTarget?.destination(at: point) }
        linkTarget.addInteraction(UIContextMenuInteraction(delegate: menu))
        linkTarget.addGestureRecognizer(UITapGestureRecognizer(target: linkTarget, action: #selector(LinkTarget.openLink(_:))))
        view.isEditable = false
        view.isSelectable = true
        view.isScrollEnabled = false
        view.backgroundColor = .clear
        view.textContainerInset = .zero
        view.textContainer.lineFragmentPadding = 0
        view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        view.accessibilityIdentifier = "profile.markdown-link-text"
        return content
    }

    func updateUIView(_ contentView: ContentView, context: Context) {
        let view = contentView.textView
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

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: ContentView, context: Context) -> CGSize? {
        let textView = uiView.textView
        let width = proposal.width ?? ceil(textView.attributedText?.size().width ?? 0)
        guard width.isFinite, width > 0 else { return nil }
        return CGSize(width: width, height: ceil(textView.sizeThatFits(CGSize(width: width, height: .greatestFiniteMagnitude)).height))
    }
}
