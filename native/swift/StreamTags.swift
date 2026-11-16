import SwiftUI
import UIKit

// Only selected pills are created. UIKit measures the same scaled system font
// used by Text; rounding up leaves room for fractional-pixel glyph advances.
struct StreamTags: View {
    let tags: [String]
    @ScaledMetric(relativeTo: .caption) private var fontSize = 12.0
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    static func widths(_ tags: [String], fontSize: CGFloat) -> [Double] {
        let font = UIFont.systemFont(ofSize: fontSize, weight: .semibold)
        return tags.map { Double(ceil(($0 as NSString).size(withAttributes: [.font: font]).width) + 17) }
    }
    var body: some View {
        GeometryReader { geometry in
            let indices = StreamTagPacking.indices(widths: Self.widths(tags, fontSize: fontSize), available: geometry.size.width)
            Group {
                if #available(iOS 26.0, *), !reduceTransparency {
                    GlassEffectContainer(spacing: 4) { pills(indices) }
                } else { pills(indices) }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        }
        .frame(height: ceil(UIFont.systemFont(ofSize: fontSize, weight: .semibold).lineHeight) + 6)
        .allowsHitTesting(false)
    }
    private func pills(_ indices: [Int]) -> some View {
        HStack(spacing: 6) {
            ForEach(indices, id: \.self) { index in pill(tags[index]) }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(indices.isEmpty ? "" : "Tags: " + indices.map { tags[$0] }.joined(separator: ", "))
    }
    private func pill(_ name: String) -> some View { StreamTagPill(name: name, fontSize: fontSize) }
}

struct StreamTagPill: View {
    let name: String
    let fontSize: CGFloat
    var multiline = false
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    var body: some View {
        let label = Text(name)
            .font(.system(size: fontSize, weight: .semibold))
            .lineLimit(multiline ? nil : 1)
            .fixedSize(horizontal: !multiline, vertical: true)
            .padding(.horizontal, 8).padding(.vertical, 3)
        if reduceTransparency {
            label.background(Color(uiColor: .secondarySystemBackground), in: Capsule())
        } else if #available(iOS 26.0, *) {
            label.glassEffect(.regular, in: Capsule())
        } else {
            label.background(.ultraThinMaterial, in: Capsule())
        }
    }
}

// Preview tags preserve native order and wrap instead of selecting a subset.
// Long individual tags can wrap too; no tag is silently dropped or ellipsized.
struct AllStreamTags: View {
    let tags: [String]
    @ScaledMetric(relativeTo: .caption) private var fontSize = 12.0
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    var body: some View {
        Group {
            if #available(iOS 26.0, *), !reduceTransparency {
                GlassEffectContainer(spacing: 4) { pills }
            } else { pills }
        }
        .allowsHitTesting(false)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Tags: " + tags.joined(separator: ", "))
    }
    private var pills: some View {
        TagFlowLayout {
            ForEach(tags, id: \.self) { StreamTagPill(name: $0, fontSize: fontSize, multiline: true) }
        }
    }
}

struct TagFlowLayout: Layout {
    private func positions(width: CGFloat, subviews: Subviews) -> (CGSize, [CGPoint], [CGSize]) {
        let width = max(1, width)
        var x: CGFloat = 0, y: CGFloat = 0, rowHeight: CGFloat = 0, usedWidth: CGFloat = 0
        var origins: [CGPoint] = [], sizes: [CGSize] = []
        for view in subviews {
            let size = view.sizeThatFits(ProposedViewSize(width: width, height: nil))
            if x > 0 && x + size.width > width { x = 0; y += rowHeight + 6; rowHeight = 0 }
            origins.append(CGPoint(x: x, y: y)); sizes.append(size)
            usedWidth = max(usedWidth, x + size.width)
            x += size.width + 6; rowHeight = max(rowHeight, size.height)
        }
        return (CGSize(width: usedWidth, height: y + rowHeight), origins, sizes)
    }
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        positions(width: proposal.width ?? 320, subviews: subviews).0
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let (_, origins, sizes) = positions(width: bounds.width, subviews: subviews)
        for index in subviews.indices {
            subviews[index].place(at: CGPoint(x: bounds.minX + origins[index].x, y: bounds.minY + origins[index].y),
                                  anchor: .topLeading, proposal: ProposedViewSize(sizes[index]))
        }
    }
}
