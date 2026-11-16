import SwiftUI
import UIKit

private struct QuickLookContent: View {
    let channel: FollowedChannel
    @ObservedObject var services: NativeServices
    @ObservedObject var playback: TheatrePlayback
    let watch: () -> Void
    let close: () -> Void
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    private var currentChannel: FollowedChannel {
        services.state.channels.first { $0.id == channel.id } ?? channel
    }
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                Color.black.opacity(reduceTransparency ? 0.85 : 0.45)
                    .ignoresSafeArea().onTapGesture(perform: close)
                    .accessibilityLabel("Dismiss stream preview").accessibilityAddTraits(.isButton)
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        ZStack(alignment: .topTrailing) {
                            ZStack {
                                PassivePlayerSurface(surface: playback.native.view).allowsHitTesting(false)
                                Button(action: watch) { Color.clear.contentShape(Rectangle()) }
                                    .buttonStyle(.plain)
                                    .accessibilityLabel("Watch stream")
                                    .accessibilityIdentifier("quicklook.video")
                            }.aspectRatio(16.0 / 9.0, contentMode: .fit)
                            HStack {
                                Label("Muted preview", systemImage: "speaker.slash.fill")
                                    .font(.caption).padding(6).background(.black.opacity(0.7), in: Capsule())
                                Spacer()
                                Button(action: close) { Image(systemName: "xmark.circle.fill").font(.title2) }
                                    .accessibilityLabel("Close preview")
                            }.foregroundStyle(.white).padding(10)
                        }
                        VStack(alignment: .leading, spacing: 10) {
                            HStack(spacing: 10) {
                                RemoteChannelImage(url: currentChannel.avatarURL, images: services.images,
                                                   generation: services.imageGeneration, avatar: true)
                                    .frame(width: 36, height: 36).clipShape(Circle())
                                    .overlay { LiveRing(clock: services.clock) }
                                Text(currentChannel.displayName).font(.headline)
                            }
                            Text(currentChannel.title.isEmpty ? "Live stream" : currentChannel.title)
                                .font(.subheadline).fixedSize(horizontal: false, vertical: true)
                            Text(currentChannel.category.isEmpty ? "Category unavailable" : currentChannel.category)
                                .font(.subheadline).foregroundStyle(.secondary)
                            if !currentChannel.tags.isEmpty { AllStreamTags(tags: currentChannel.tags) }
                            if playback.phase != 3 {
                                HStack {
                                    if [1, 2, 4].contains(playback.phase) { ProgressView() }
                                    Text(playback.message).font(.caption).foregroundStyle(.secondary)
                                }
                            }
                            Divider()
                            Button(action: watch) { Label("Watch stream", systemImage: "play.fill").frame(maxWidth: .infinity, alignment: .leading) }
                                .padding(.vertical, 6).accessibilityIdentifier("quicklook.watch")
                            Button {} label: { Label("View profile", systemImage: "person.fill").frame(maxWidth: .infinity, alignment: .leading) }
                                .disabled(true).padding(.vertical, 6)
                                .accessibilityHint("Not available yet")
                        }.padding(.horizontal, 16).padding(.bottom, 16)
                    }
                }
                .frame(maxWidth: 420, maxHeight: max(100, min(660, geometry.size.height - 40)))
                .background(Color(uiColor: .systemBackground), in: RoundedRectangle(cornerRadius: 20))
                .clipShape(RoundedRectangle(cornerRadius: 20))
                .padding(.horizontal, 20)
                .accessibilityIdentifier("quicklook.card")
            }
        }
        .onChange(of: services.state.session) { session in
            if session != .authenticated { playback.stop(); close() }
        }
        .task {
            while !Task.isCancelled {
                playback.update()
                do { try await Task.sleep(nanoseconds: 250_000_000) } catch { return }
            }
        }
    }
}

@MainActor
enum NativeQuickLook {
    static func controller(channel: FollowedChannel, services: NativeServices, close: @escaping () -> Void) -> UIViewController {
        let playback = TheatrePlayback(channel: channel.username)
        // Set intent before start, before authorization finishes, and before IVS
        // load/play. The same intent survives background player recreation.
        playback.setMuted(true)
        weak var owner: QuickLookController?
        let preview = UIHostingController(rootView: QuickLookContent(channel: channel, services: services,
                                                                    playback: playback, watch: { owner?.watch() }, close: close))
        preview.view.backgroundColor = .clear
        preview.view.accessibilityViewIsModal = true
        let controller = QuickLookController(preview: preview, makeTheatre: {
            NativeTheatre.controller(channel: channel, services: services, playback: playback, close: close)
        }, start: playback.start, watched: { playback.setMuted(false) }, stop: playback.stop)
        owner = controller
        return controller
    }
}
