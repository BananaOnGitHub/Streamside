import SwiftUI
import UIKit

private struct RemoteChannelImage: View {
    let url: URL?
    let images: ChannelImageCache
    let generation: UInt64
    var avatar = false
    var restricted = false
    @State private var image: UIImage?
    private var requestID: String { "\(generation)|\(url?.absoluteString ?? "")" }
    var body: some View {
        ZStack {
            Color(uiColor: .secondarySystemBackground)
            if let image { Image(uiImage: image).resizable().scaledToFill() }
            else { Image(systemName: avatar ? "person.fill" : restricted ? "eye.slash" : "photo").foregroundStyle(.secondary) }
        }
        .clipped()
        .task(id: requestID) {
            guard let url else { image = nil; return }
            let fetched = await images.load(url: url, generation: generation, avatar: avatar)
            guard !Task.isCancelled else { return }
            image = fetched
        }
        .accessibilityHidden(true)
    }
}

struct LiveChannelRow: View {
    let channel: FollowedChannel
    let images: ChannelImageCache
    let generation: UInt64
    @Environment(\.dynamicTypeSize) private var typeSize
    @Environment(\.scenePhase) private var scenePhase

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
        .padding(.vertical, 5)
        .listRowSeparator(.hidden)
        .accessibilityElement(children: .combine)
        .accessibilityValue("Live")
    }
    private var thumbnail: some View {
        RemoteChannelImage(url: channel.thumbnailURL, images: images, generation: generation, restricted: channel.thumbnailRestricted)
            .aspectRatio(16.0 / 9.0, contentMode: .fit)
            .overlay(alignment: .bottomTrailing) {
                if let started = channel.startedAt {
                    StreamTimePill(startedAt: started, active: scenePhase == .active).padding(4)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 7))
    }
    private var details: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                RemoteChannelImage(url: channel.avatarURL, images: images, generation: generation, avatar: true)
                    .frame(width: 22, height: 22)
                    .clipShape(Circle())
                    .overlay(Circle().stroke(.red, lineWidth: 1.5))
                Text(channel.displayName).font(.headline).lineLimit(1)
            }
            Text(channel.title.isEmpty ? "Live stream" : channel.title)
                .font(.subheadline).lineLimit(typeSize.isAccessibilitySize ? 3 : 1)
            Text(channel.category.isEmpty ? "Category unavailable" : channel.category)
                .font(.caption).foregroundStyle(.secondary).lineLimit(1)
            if let viewers = channel.viewerCount {
                Text("\(viewers.formatted()) viewers").font(.caption).foregroundStyle(.secondary)
            } else {
                Text("Viewers unavailable").font(.caption).foregroundStyle(.secondary)
            }
        }
    }
}

struct OfflineChannelRow: View {
    let channel: FollowedChannel
    let images: ChannelImageCache
    let generation: UInt64
    var body: some View {
        HStack(spacing: 10) {
            RemoteChannelImage(url: channel.avatarURL, images: images, generation: generation, avatar: true)
                .frame(width: 28, height: 28).clipShape(Circle())
            Text(channel.displayName).lineLimit(1)
            Spacer()
            Text("Offline").font(.caption).foregroundStyle(.secondary)
        }
        .accessibilityElement(children: .combine)
    }
}

private struct StreamTimePill: View {
    let startedAt: Date
    let active: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    var body: some View {
        TimelineView(.animation(minimumInterval: 1, paused: !active)) { context in
            let elapsed = StreamElapsed.seconds(startedAt: startedAt, now: context.date)
            timerLabel(elapsed: elapsed)
                .accessibilityLabel("Stream duration")
                .accessibilityValue(StreamElapsed.label(seconds: elapsed))
        }
    }
    @ViewBuilder private func timerLabel(elapsed: Int) -> some View {
        let label = Text(StreamElapsed.label(seconds: elapsed))
            .font(.system(size: 10, weight: .semibold, design: .monospaced))
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
