import SwiftUI
import UIKit

@MainActor private struct NativeProfileBackend: ChannelProfileBackend {
    let valid: () -> Bool
    func request(channelID: String, operation: ProfileOperation, setting: String) async throws -> [String: Any] {
        let request = SSNProfileRequest(channelID: channelID, operation: operation.rawValue, setting: setting)
        defer { request.cancel() }
        while !Task.isCancelled {
            guard valid() else { throw CancellationError() }
            request.poll()
            if request.phase == 1 { return request.result }
            if request.phase != 0 { throw CocoaError(.coderReadCorrupt) }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        throw CancellationError()
    }
}

// One inline muted player. Tab changes retire it; Watch transfers the exact
// facade only after the profile presentation has dismissed. Audio is promoted
// by the existing theatre host, never by a profile or a dismissal animation.
@MainActor private final class ProfileMedia: ObservableObject {
    @Published private(set) var playback: TheatrePlayback?
    private var transferring = false
    func start(channel: FollowedChannel, services: NativeServices, account: StreamsideAccount?, close: @escaping () -> Void) {
        guard playback == nil else { return }
        let player = TheatrePlayback(channel: channel.username, preview: true, localTest: channel.localTest)
        player.setMuted(true)
        player.bindContentOwner(valid: {
            SSNNavigationPermitted() && UIApplication.shared.applicationState == .active &&
            services.state.session == .authenticated && services.state.account == account
        }, close: close)
        services.prepareContentGate(channel, playback: player)
        playback = player; player.startIfNeeded()
    }
    func stop() { guard !transferring else { return }; playback?.stop(); playback = nil }
    func watch(_ action: (TheatrePlayback) -> Bool) {
        guard !transferring, let playback else { return }
        transferring = true
        if !action(playback) { transferring = false; stop() }
    }
}

private struct ProfileLivePreview: View {
    @ObservedObject var playback: TheatrePlayback
    let watch: () -> Void
    var body: some View {
        VStack(spacing: 10) {
            Color.black.aspectRatio(16.0 / 9.0, contentMode: .fit).overlay {
                if let gate = playback.contentGate { MarkedContentWarning(gate: gate) }
                else if playback.localTest != nil { LocalTestMedia() }
                else if let native = playback.native {
                    PassivePlayerSurface(surface: native.view, topCornerRadius: 16)
                        .overlay(alignment: .bottomTrailing) {
                            Image(systemName: "speaker.slash.fill").font(.caption2).padding(6)
                                .background(.black.opacity(0.5), in: Capsule()).padding(8)
                                .foregroundStyle(.white).allowsHitTesting(false)
                        }
                        .contentShape(Rectangle()).onTapGesture(perform: watch)
                }
            }.clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            if playback.contentGate == nil {
                PreviewPlaybackStatus(phase: playback.phase, message: playback.message)
                Button(action: watch) { Label("Watch stream", systemImage: "play.fill") }
                    .buttonStyle(.bordered).accessibilityIdentifier("profile.watch")
            }
        }.task {
            while !Task.isCancelled {
                playback.update()
                do { try await Task.sleep(nanoseconds: 250_000_000) } catch { return }
            }
        }
    }
}

private struct ProfileContent: View {
    @ObservedObject var services: NativeServices
    @StateObject var model: ChannelProfileModel
    @StateObject private var media = ProfileMedia()
    let account: StreamsideAccount?
    let close: () -> Void
    let watch: (TheatrePlayback) -> Bool
    var body: some View {
        ChannelProfileView(model: model, images: services.images, clock: services.clock, close: close) {
            Group {
                if let playback = media.playback { ProfileLivePreview(playback: playback) { media.watch(watch) } }
                else { Color.black.aspectRatio(16.0 / 9.0, contentMode: .fit) }
            }
        }
        .onAppear { if model.tab == 0 { startMedia() } }
        .onDisappear { media.stop() }
        .onChange(of: model.tab) { if $0 == 0 { startMedia() } else { media.stop() } }
        .onChange(of: services.state.session) { if $0 != .authenticated { media.stop(); close() } }
        .onChange(of: services.state.account) { if $0 != account { media.stop(); close() } }
        .onReceive(NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)) { _ in media.stop() }
        .onReceive(NotificationCenter.default.publisher(for: UIApplication.didBecomeActiveNotification)) { _ in if model.tab == 0 { startMedia() } }
    }
    private func startMedia() {
        guard model.channel.isLive, model.channel.playbackAllowed, services.state.session == .authenticated,
              services.state.account == account, UIApplication.shared.applicationState == .active else { return }
        media.start(channel: model.channel, services: services, account: account, close: close)
    }
}

@MainActor enum NativeProfile {
    static func controller(channel: FollowedChannel, services: NativeServices, close: @escaping () -> Void,
                           watch: @escaping (TheatrePlayback) -> Bool) -> UIViewController {
        let account = services.state.account
        let valid = {
            SSNNavigationPermitted() && UIApplication.shared.applicationState == .active &&
            services.state.session == .authenticated && services.state.account == account
        }
        let model = ChannelProfileModel(channel: channel, backend: NativeProfileBackend(valid: valid), valid: valid,
            changed: { services.refreshPlayerInfo() }, rejected: { SSNProfileResponseRejected($0.rawValue) })
        let controller = UIHostingController(rootView: ProfileContent(services: services, model: model, account: account, close: close, watch: watch))
        controller.modalPresentationStyle = .fullScreen
        controller.modalTransitionStyle = .crossDissolve
        return controller
    }
}
