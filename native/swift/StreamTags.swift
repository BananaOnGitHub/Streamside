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
    @ViewBuilder private func pill(_ name: String) -> some View {
        let label = Text(name)
            .font(.system(size: fontSize, weight: .semibold))
            .lineLimit(1).fixedSize()
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
