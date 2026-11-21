import SwiftUI
import UIKit

struct PanelMarkdownView: View {
    let markdown: PanelMarkdown
    let previewSize: CGSize
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(markdown.blocks) { PanelMarkdownBlockView(block: $0, previewSize: previewSize, accent: accent) }
        }
        .font(.subheadline)
        .textSelection(.enabled)
    }
}

private struct PanelMarkdownBlockView: View {
    let block: PanelMarkdown.Block
    let previewSize: CGSize
    let accent: Color
    var numbered = false

    var body: some View {
        switch block.kind {
        case .header(let level):
            inlineText(bold: true, heading: level)
                .accessibilityAddTraits(.isHeader)
                .accessibilityIdentifier("profile.panel-heading")
        case .blockQuote:
            children
                .padding(.leading, 10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(alignment: .leading) {
                    Capsule().fill(accent.opacity(0.45)).frame(width: 2)
                }
        case .unorderedList, .orderedList:
            VStack(alignment: .leading, spacing: 4) {
                ForEach(block.children) { nested($0, numbered: block.kind == .orderedList) }
            }
        case .listItem(let number):
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(numbered ? "\(number)." : "•").foregroundStyle(.secondary)
                children
            }
        case .codeBlock:
            ScrollView(.horizontal) {
                Text(block.text).font(.system(.footnote, design: .monospaced))
                    .fixedSize(horizontal: true, vertical: false).padding(10)
            }
            .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
        case .thematicBreak:
            Divider()
        case .table:
            ScrollView(.horizontal) {
                Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 8) {
                    ForEach(block.children) { row in
                        GridRow {
                            ForEach(row.children) { cell in
                                nested(cell)
                                    .fontWeight(row.kind == .tableHeaderRow ? .semibold : .regular)
                            }
                        }
                    }
                }
                .padding(8)
            }
            .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
        default:
            if block.children.isEmpty { inlineText() }
            else { children }
        }
    }

    private var children: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(block.children) { nested($0) }
        }
    }

    private func nested(_ block: PanelMarkdown.Block, numbered: Bool = false) -> some View {
        PanelMarkdownBlockView(block: block, previewSize: previewSize, accent: accent, numbered: numbered)
    }

    @ViewBuilder private func inlineText(bold: Bool = false, heading: Int? = nil) -> some View {
        let styles: (Font, UIFont.TextStyle) = switch heading {
        case 1: (.title2, .title2)
        case 2: (.title3, .title3)
        case .some: (.headline, .headline)
        case nil: (.subheadline, .subheadline)
        }
        if #available(iOS 17.0, *), block.text.runs.contains(where: { $0.link != nil }) {
            PanelMarkdownLinkText(text: block.text, style: styles.1, bold: bold, accent: accent, previewSize: previewSize)
        } else {
            Text(block.text).font(bold ? styles.0.bold() : styles.0)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}
