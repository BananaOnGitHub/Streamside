import SwiftUI
import UIKit

struct RemoteChannelImage: View {
    let url: URL?
    let images: ChannelImageCache
    let generation: UInt64
    var localImage: UIImage? = nil
    var avatar = false
    var restricted = false
    var thumbnailActions: ThumbnailActions?
    @State private var image: UIImage?
    private var requestID: String { "\(generation)|\(restricted)|\(url?.absoluteString ?? "")" }
    private var displayedImage: UIImage? { localImage ?? image }
    private var configuredActions: ThumbnailActions? {
        var actions = thumbnailActions
        actions?.image = restricted ? nil : displayedImage
        return actions
    }
    var body: some View {
        ZStack {
            Color(uiColor: .secondarySystemBackground)
            if let actions = configuredActions {
                actions
                if displayedImage == nil || restricted {
                    Image(systemName: restricted ? "eye.slash" : "photo").foregroundStyle(.secondary).allowsHitTesting(false)
                }
            } else if let image = displayedImage, !restricted { Image(uiImage: image).resizable().scaledToFill() }
            else { Image(systemName: avatar ? "person.fill" : restricted ? "eye.slash" : "photo").foregroundStyle(.secondary) }
        }
        .clipped()
        .task(id: requestID) {
            guard !restricted, let url else { image = nil; return }
            let fetched = await images.load(url: url, generation: generation, avatar: avatar)
            guard !Task.isCancelled else { return }
            image = fetched
        }
        .accessibilityHidden(thumbnailActions == nil)
    }
}

struct LiveChannelRow: View {
    let channel: FollowedChannel
    let images: ChannelImageCache
    let generation: UInt64
    @Environment(\.dynamicTypeSize) private var typeSize
    let clock: StreamClock
    let haptics: TitleHaptics
    let open: () -> Void
    let preview: (UIView) -> ContextPreviewSession?
    var profile: (() -> Void)?
    var authorizePreview: ((UIView, @escaping (Bool) -> Void) -> Void)?
    @AppStorage(MarkedContentPreferences.thumbnailsKey) private var markedThumbnails = false
    @AppStorage(FeedPreferences.twoLineTitlesKey) private var twoLineTitles = false
    @State private var showFullTitle = false
    @State private var titleMeasurement: TitleMeasurement?
    @State private var holdOwner = UUID()
    private var displayedTitle: String { channel.title.isEmpty ? "Live stream" : channel.title }
    private var titleLines: Int {
        FeedPreferences.titleLines(twoLines: twoLineTitles, phone: UIDevice.current.userInterfaceIdiom == .phone, accessible: typeSize.isAccessibilitySize)
    }
    private var canPreviewTitle: Bool {
        titleMeasurement?.text == displayedTitle && titleMeasurement?.lines == titleLines && titleMeasurement?.truncated == true
    }
    private func openTitle() {
        guard canPreviewTitle else { return }
        haptics.opened(); showFullTitle = true
    }

    var body: some View {
        Group {
            if typeSize.isAccessibilitySize {
                VStack(alignment: .leading, spacing: 10) { thumbnail; details }
            } else {
                HStack(alignment: .center, spacing: 12) {
                    thumbnail.frame(width: 140)
                    details.frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .contentShape(Rectangle())
        .accessibilityAction(named: "Watch live stream", open)
        .padding(.vertical, 2)
        .listRowSeparator(.hidden)
        .accessibilityElement(children: .contain)
        .accessibilityValue("Live")
        .accessibilityActions {
            if canPreviewTitle { Button("Show full stream title") { openTitle() } }
        }
        .onDisappear { haptics.cancel(owner: holdOwner) }
        .onChange(of: canPreviewTitle) { available in
            if !available { haptics.cancel(owner: holdOwner); showFullTitle = false }
        }
        .popover(isPresented: $showFullTitle, attachmentAnchor: .rect(.bounds), arrowEdge: .bottom) {
            FullStreamTitle(channel: channel)
                .presentationCompactAdaptation(.popover)
                .presentationBackground(.regularMaterial)
        }
    }
    private var thumbnail: some View {
        RemoteChannelImage(url: channel.thumbnailURL, images: images, generation: generation, localImage: channel.localTest == nil ? nil : LocalTestArtwork.thumbnail, restricted: !channel.playbackAllowed || (channel.thumbnailRestricted && !markedThumbnails),
                           thumbnailActions: ThumbnailActions(label: channel.displayName + " stream thumbnail", open: open, preview: preview, authorizePreview: authorizePreview))
            .aspectRatio(16.0 / 9.0, contentMode: .fit)
            .overlay(alignment: .bottomTrailing) {
                if let started = channel.startedAt {
                    StreamTimePill(startedAt: started, clock: clock).padding(4).allowsHitTesting(false)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 7))
    }
    private var details: some View {
        VStack(alignment: .leading, spacing: 4) {
            Button { profile?() } label: {
                HStack(spacing: 6) {
                RemoteChannelImage(url: channel.avatarURL, images: images, generation: generation, localImage: channel.localTest == nil ? nil : LocalTestArtwork.avatar, avatar: true)
                    .frame(width: 22, height: 22)
                    .clipShape(Circle())
                    .overlay { LiveRing(clock: clock) }
                VerifiedChannelName(channel: channel).font(.headline)
                }
            }.buttonStyle(.plain).accessibilityLabel("View " + channel.displayName + " profile")
            VStack(alignment: .leading, spacing: 4) {
                MeasuredStreamTitle(text: displayedTitle, lines: titleLines) { titleMeasurement = $0 }
                    .modifier(TitleHold(enabled: canPreviewTitle, haptics: haptics, owner: holdOwner, open: openTitle))
                    .accessibilityHint(canPreviewTitle ? "Hold for the full stream title" : "")
                Text(channel.category.isEmpty ? "Category unavailable" : channel.category)
                    .font(.caption).foregroundStyle(.secondary).lineLimit(1)
                if !channel.tags.isEmpty { StreamTags(tags: channel.tags) }
                if let viewers = channel.viewerCount {
                    Text("\(viewers.formatted()) viewers").font(.caption).foregroundStyle(.secondary)
                } else {
                    Text("Viewers unavailable").font(.caption).foregroundStyle(.secondary)
                }
            }.contentShape(Rectangle()).onTapGesture(perform: open)
        }.accessibilityElement(children: .contain)
    }
}

struct OfflineChannelRow: View {
    let channel: FollowedChannel
    let images: ChannelImageCache
    let generation: UInt64
    var profile: (() -> Void)?
    var body: some View {
        Button { profile?() } label: {
            HStack(spacing: 10) {
            RemoteChannelImage(url: channel.avatarURL, images: images, generation: generation, localImage: channel.localTest == nil ? nil : LocalTestArtwork.avatar, avatar: true)
                .frame(width: 28, height: 28).clipShape(Circle())
            VerifiedChannelName(channel: channel)
            Spacer()
            Text("Offline").font(.caption).foregroundStyle(.secondary)
            }
        }.buttonStyle(.plain).accessibilityLabel("View " + channel.displayName + " profile")
    }
}

private struct StreamTimePill: View {
    let startedAt: Date
    @ObservedObject var clock: StreamClock
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    var body: some View {
        let elapsed = StreamElapsed.seconds(startedAt: startedAt, now: clock.now)
        timerLabel(elapsed: elapsed)
            .accessibilityLabel("Stream duration")
            .accessibilityValue(StreamElapsed.label(seconds: elapsed))
    }
    @ViewBuilder private func timerLabel(elapsed: Int) -> some View {
        let label = Text(StreamElapsed.label(seconds: elapsed))
            .font(.system(size: 10, weight: .medium))
            .monospacedDigit()
            .contentTransition(reduceMotion ? .identity : .numericText(countsDown: false))
            .animation(reduceMotion ? nil : .easeInOut(duration: 0.2), value: elapsed)
            .padding(.horizontal, 5).padding(.vertical, 2)
        if reduceTransparency {
            label.foregroundStyle(.white).background(.black.opacity(0.9), in: Capsule())
        } else if #available(iOS 26.0, *) {
            label.glassEffect(.regular, in: Capsule())
        } else {
            label.background(.ultraThinMaterial, in: Capsule())
        }
    }
}

private struct FullStreamTitle: View {
    let channel: FollowedChannel
    private var title: some View {
        Text(channel.title.isEmpty ? "Live stream" : channel.title)
            .font(.body).textSelection(.enabled)
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
    var body: some View {
        ViewThatFits(in: .vertical) {
            title
            ScrollView { title }
        }
        .frame(idealWidth: 300, maxWidth: 320, maxHeight: 220)
        .padding(14)
        .accessibilityLabel("Full stream title")
    }
}

private struct TitleHold: ViewModifier {
    let enabled: Bool
    let haptics: TitleHaptics
    let owner: UUID
    let open: () -> Void
    @ViewBuilder func body(content: Content) -> some View {
        if enabled {
            content.contentShape(Rectangle()).onLongPressGesture(minimumDuration: 1, maximumDistance: 10, pressing: { pressing in
                if pressing { haptics.begin(owner: owner) } else { haptics.cancel(owner: owner) }
            }, perform: open)
        } else { content }
    }
}
