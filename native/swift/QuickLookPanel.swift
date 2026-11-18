import SwiftUI

// Interactive content for the owned source-anchored presenter.
struct QuickLookPanel<Video: View, Details: View, Status: View>: View {
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    let width: CGFloat
    let detailsHeight: CGFloat
    let video: () -> Video
    let details: () -> Details
    let status: () -> Status
    init(width: CGFloat, detailsHeight: CGFloat, @ViewBuilder video: @escaping () -> Video,
         @ViewBuilder details: @escaping () -> Details, @ViewBuilder status: @escaping () -> Status) {
        self.width = width; self.detailsHeight = detailsHeight
        self.video = video; self.details = details; self.status = status
    }
    var body: some View {
        GeometryReader { geometry in
            VStack(spacing: 0) {
                video().frame(width: width, height: width * 9 / 16).clipped()
                information(height: max(1, min(detailsHeight, geometry.size.height - width * 9 / 16)))
            }
        }
        .frame(width: width)
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("quicklook.card")
    }
    @ViewBuilder private func information(height: CGFloat) -> some View {
        let content = VStack(spacing: 0) {
            ScrollView { details().frame(maxWidth: .infinity, alignment: .leading).padding(16) }
                .scrollBounceBehavior(.basedOnSize)
            status().layoutPriority(1)
        }.frame(height: height)
        if reduceTransparency {
            content.background(Color(uiColor: .secondarySystemBackground))
        } else if #available(iOS 26.0, *) {
            content.glassEffect(.regular, in: Rectangle())
        } else {
            content.background(.regularMaterial)
        }
    }
}

extension QuickLookPanel where Status == EmptyView {
    init(width: CGFloat, detailsHeight: CGFloat, @ViewBuilder video: @escaping () -> Video,
         @ViewBuilder details: @escaping () -> Details) {
        self.init(width: width, detailsHeight: detailsHeight, video: video, details: details, status: { EmptyView() })
    }
}

// Status stays outside the scrollable title/tags, with its own bottom inset.
// It cannot be stranded below a long title or clipped by the rounded card edge.
struct PreviewPlaybackStatus: View {
    let phase: Int
    let message: String
    var body: some View {
        if phase != 3 {
            HStack(spacing: 8) {
                if [1, 2, 4].contains(phase) {
                    ProgressView().controlSize(.small).frame(width: 16, height: 16)
                        .accessibilityIdentifier("quicklook.buffering-spinner")
                }
                Text(message).font(.caption).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 16).padding(.bottom, 12)
        }
    }
}
