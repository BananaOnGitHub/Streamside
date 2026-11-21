import Foundation

struct PanelMarkdown {
    struct Block: Identifiable {
        let id: Int
        let kind: PresentationIntent.Kind
        var text = AttributedString()
        var children: [Block] = []

        mutating func append(_ text: AttributedString, at path: ArraySlice<PresentationIntent.IntentType>) {
            guard let entry = path.first else { self.text.append(text); return }
            if children.last?.id != entry.identity {
                children.append(Block(id: entry.identity, kind: entry.kind))
            }
            children[children.count - 1].append(text, at: path.dropFirst())
        }
    }

    let blocks: [Block]

    init(_ source: String) {
        var root = Block(id: 0, kind: .paragraph)
        if let parsed = try? AttributedString(markdown: source, options: .init(interpretedSyntax: .full)) {
            let formatted = Self.webLinksOnly(parsed)
            for run in formatted.runs {
                guard let intent = run.presentationIntent else { continue }
                // The parser assigns each enclosing block its identity
                // before visiting its children.
                let path = intent.components.sorted { $0.identity < $1.identity }
                let text = run.inlinePresentationIntent?.contains(.softBreak) == true
                    ? AttributedString("\n") : AttributedString(formatted[run.range])
                root.append(text, at: path[...])
            }
        }
        if root.children.allSatisfy({ $0.kind == .paragraph }) {
            // Plain descriptions often use one line per credit. Keep their
            // exact whitespace, including when the only markup is inline.
            let inline = (try? AttributedString(markdown: source,
                options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace))) ?? AttributedString(source)
            blocks = inline.characters.isEmpty ? [] : [Block(id: 0, kind: .paragraph, text: Self.webLinksOnly(inline))]
        } else {
            blocks = root.children
        }
    }

    private static func webLinksOnly(_ content: AttributedString) -> AttributedString {
        var formatted = content
        for run in content.runs {
            if let destination = run.link, ChannelProfileData.url(destination.absoluteString) == nil {
                formatted[run.range].link = nil
            }
        }
        return formatted
    }
}
