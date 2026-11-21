import SwiftUI

struct PanelMarkdownView: View {
    let markdown: PanelMarkdown

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(markdown.blocks) { PanelMarkdownBlockView(block: $0) }
        }
        .font(.subheadline)
        .textSelection(.enabled)
    }
}

private struct PanelMarkdownBlockView: View {
    let block: PanelMarkdown.Block
    var numbered = false

    var body: some View {
        switch block.kind {
        case .header(let level):
            Text(block.text)
                .font(headingFont(level).bold())
                .accessibilityAddTraits(.isHeader)
                .accessibilityIdentifier("profile.panel-heading")
        case .blockQuote:
            children
                .padding(.leading, 10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(alignment: .leading) {
                    Capsule().fill(Color.secondary.opacity(0.45)).frame(width: 2)
                }
        case .unorderedList, .orderedList:
            VStack(alignment: .leading, spacing: 4) {
                ForEach(block.children) { PanelMarkdownBlockView(block: $0, numbered: block.kind == .orderedList) }
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
                                PanelMarkdownBlockView(block: cell)
                                    .fontWeight(row.kind == .tableHeaderRow ? .semibold : .regular)
                            }
                        }
                    }
                }
                .padding(8)
            }
            .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
        default:
            if block.children.isEmpty { Text(block.text).fixedSize(horizontal: false, vertical: true) }
            else { children }
        }
    }

    private var children: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(block.children) { PanelMarkdownBlockView(block: $0) }
        }
    }

    private func headingFont(_ level: Int) -> Font {
        switch level {
        case 1: return .title2
        case 2: return .title3
        default: return .headline
        }
    }
}
