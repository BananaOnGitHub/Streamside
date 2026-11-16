import SwiftUI
import UIKit

private struct QuickLookContent: View {
    let channel: FollowedChannel
    @ObservedObject var services: NativeServices
    @ObservedObject var playback: TheatrePlayback
    let watch: () -> Void
    let close: () -> Void
    private var currentChannel: FollowedChannel {
        services.state.channels.first { $0.id == channel.id } ?? channel
    }
    var body: some View {
        QuickLookPanel(watch: watch, close: close) {
            ZStack(alignment: .topTrailing) {
                ZStack {
                    PassivePlayerSurface(surface: playback.native.view).allowsHitTesting(false)
                    Button(action: watch) { Color.clear.contentShape(Rectangle()) }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Watch stream")
                        .accessibilityIdentifier("quicklook.video")
                }
                HStack {
                    Image(systemName: "speaker.slash.fill")
                        .font(.caption).padding(8).background(.black.opacity(0.55), in: Circle())
                        .accessibilityLabel("Muted preview")
                    Spacer()
                    Button(action: close) { Image(systemName: "xmark").font(.body.weight(.semibold)).frame(width: 44, height: 44) }
                        .background(.black.opacity(0.55), in: Circle())
                        .accessibilityLabel("Close preview")
                }.foregroundStyle(.white).padding(8)
            }
        } details: {
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
                HStack {
                    if [1, 2, 4].contains(playback.phase) { ProgressView() }
                    Text(playback.phase == 3 ? "Live · Muted preview" : playback.message)
                        .font(.caption).foregroundStyle(.secondary)
                }
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
