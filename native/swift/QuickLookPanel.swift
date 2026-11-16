import SwiftUI

// Content only. UIKit supplies the native menu, backdrop, lift and dismissal.
struct QuickLookPanel<Video: View, Details: View>: View {
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    let width: CGFloat
    let detailsHeight: CGFloat
    let video: () -> Video
    let details: () -> Details
    init(width: CGFloat, detailsHeight: CGFloat, @ViewBuilder video: @escaping () -> Video,
         @ViewBuilder details: @escaping () -> Details) {
        self.width = width; self.detailsHeight = detailsHeight
        self.video = video; self.details = details
    }
    var body: some View {
        VStack(spacing: 0) {
            video().frame(width: width, height: width * 9 / 16).clipped()
            information
        }
        .frame(width: width)
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("quicklook.card")
    }
    @ViewBuilder private var information: some View {
        let content = ScrollView { details().frame(maxWidth: .infinity, alignment: .leading).padding(16) }
            .scrollBounceBehavior(.basedOnSize).frame(height: detailsHeight)
        if reduceTransparency {
            content.background(Color(uiColor: .secondarySystemBackground))
        } else if #available(iOS 26.0, *) {
            content.glassEffect(.regular, in: Rectangle())
        } else {
            content.background(.regularMaterial)
        }
    }
}
