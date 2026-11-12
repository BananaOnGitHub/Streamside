import SwiftUI
import UIKit

struct TitleMeasurement: Equatable {
    let text: String
    let lines: Int
    let width: CGFloat
    let fontSize: CGFloat
    let truncated: Bool
}

// Render and measure with the same UIKit font and line-breaking engine. Character
// counts cannot determine clipping for emoji, different widths, or Dynamic Type.
final class StreamTitleLabel: UILabel {
    var measured: ((TitleMeasurement) -> Void)?
    private let fullLabel = UILabel()
    private var lastMeasurement: TitleMeasurement?

    func isTruncated(atWidth width: CGFloat) -> Bool {
        guard width > 0, let text, !text.isEmpty, numberOfLines > 0 else { return false }
        fullLabel.text = text
        fullLabel.font = font
        fullLabel.numberOfLines = 0
        fullLabel.lineBreakMode = .byWordWrapping
        fullLabel.semanticContentAttribute = semanticContentAttribute
        let proposal = CGSize(width: width, height: CGFloat.greatestFiniteMagnitude)
        let full = fullLabel.sizeThatFits(proposal).height
        let limited = sizeThatFits(proposal).height
        return full > limited + 0.5
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        guard bounds.width > 0 else { return }
        let next = TitleMeasurement(text: text ?? "", lines: numberOfLines,
                                    width: bounds.width, fontSize: font.pointSize,
                                    truncated: isTruncated(atWidth: bounds.width))
        guard lastMeasurement != next else { return }
        lastMeasurement = next
        DispatchQueue.main.async { [weak self] in
            guard let self, self.lastMeasurement == next else { return }
            self.measured?(next)
        }
    }
}

struct MeasuredStreamTitle: UIViewRepresentable {
    let text: String
    let lines: Int
    let measured: (TitleMeasurement) -> Void

    func makeUIView(context: Context) -> StreamTitleLabel {
        let label = StreamTitleLabel()
        label.adjustsFontForContentSizeCategory = true
        label.lineBreakMode = .byTruncatingTail
        label.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        return label
    }
    func updateUIView(_ label: StreamTitleLabel, context: Context) {
        label.text = text
        label.font = .preferredFont(forTextStyle: .subheadline, compatibleWith: label.traitCollection)
        label.numberOfLines = lines
        label.textColor = .label
        label.measured = measured
        label.setNeedsLayout()
    }
    func sizeThatFits(_ proposal: ProposedViewSize, uiView: StreamTitleLabel, context: Context) -> CGSize? {
        guard let width = proposal.width, width > 0 else { return nil }
        let size = uiView.sizeThatFits(CGSize(width: width, height: CGFloat.greatestFiniteMagnitude))
        return CGSize(width: width, height: ceil(size.height))
    }
}
