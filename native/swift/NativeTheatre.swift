import SwiftUI
import UIKit

private struct TheatreContent: View {
    let channel: FollowedChannel
    @ObservedObject var services: NativeServices
    let close: () -> Void
    let account: StreamsideAccount?
    @StateObject private var playback: TheatrePlayback
    @State private var controls = PlayerControlsVisibility()
    @State private var overlayPresented = false
    @State private var voiceOver = UIAccessibility.isVoiceOverRunning
    private var currentChannel: FollowedChannel {
        services.state.channels.first { $0.id == channel.id } ?? channel
    }
    private func interact() { controls.reveal(now: ProcessInfo.processInfo.systemUptime) }
    init(channel: FollowedChannel, services: NativeServices, playback: TheatrePlayback, close: @escaping () -> Void) {
        self.channel = channel; self.services = services; self.close = close; self.account = services.state.account
        _playback = StateObject(wrappedValue: playback)
    }
    var body: some View {
        VStack(spacing: 0) {
            if let gate = playback.contentGate {
                // The canvas owns video geometry, not the warning's ideal size.
                Color.black.aspectRatio(16.0 / 9.0, contentMode: .fit)
                    .overlay { MarkedContentWarning(gate: gate) }
            } else {
                PlayerCanvas(surface: playback.native.view, toggleControls: {
                    SSNPlayerControlEvent(0)
                    controls.toggle(now: ProcessInfo.processInfo.systemUptime)
                }) {
                    PlayerControls(visible: controls.visible, channel: currentChannel, clock: services.clock,
                                   paused: playback.paused, muted: playback.muted,
                                   close: { playback.stop(); close() }, pause: playback.togglePaused,
                                   mute: playback.toggleMuted, interact: interact,
                                   presentationChanged: { overlayPresented = $0 })
                }
            }
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 10) {
                    RemoteChannelImage(url: currentChannel.avatarURL, images: services.images,
                        generation: services.imageGeneration, avatar: true)
                        .frame(width: 32, height: 32).clipShape(Circle())
                    VerifiedChannelName(channel: currentChannel).font(.headline)
                }
                Text(currentChannel.title).font(.subheadline).lineLimit(2)
                HStack {
                    if playback.phase == 1 || playback.phase == 2 || playback.phase == 4 { ProgressView() }
                    Text(playback.contentGate == nil ? playback.message : "Review the content warning to continue.").font(.footnote).foregroundStyle(.secondary)
                    Spacer(minLength: 0)
                    if playback.phase == 6 || playback.phase == 7 {
                        Button("Retry") { playback.start() }.disabled(playback.error == 1)
                    }
                }
            }.padding()
            Divider()
            Spacer()
            Text("Chat is not available yet").font(.footnote).foregroundStyle(.secondary)
            Spacer()
        }
        .background(Color(uiColor: .systemBackground))
        .onAppear { playback.startIfNeeded(); interact() }
        .onDisappear { playback.stop() }
        .task {
            while !Task.isCancelled {
                playback.update()
                controls.tick(now: ProcessInfo.processInfo.systemUptime,
                              keepVisible: playback.contentGate != nil || overlayPresented || voiceOver)
                do { try await Task.sleep(nanoseconds: 250_000_000) } catch { return }
            }
        }
        .onChange(of: services.state.session) { session in
            if session != .authenticated { playback.stop(); close() }
        }
        .onChange(of: services.state.account) { if $0 != account { playback.stop(); close() } }
        .onReceive(NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)) { _ in
            if playback.contentGate != nil { playback.stop(); close() }
        }
        .onReceive(NotificationCenter.default.publisher(for: UIAccessibility.voiceOverStatusDidChangeNotification)) { _ in
            voiceOver = UIAccessibility.isVoiceOverRunning; interact()
        }
        .task {
            // Reuse the authenticated native account/feed client, with its request
            // guard. Do not reload thumbnails or poll when the app is inactive.
            while !Task.isCancelled {
                do { try await Task.sleep(nanoseconds: 30_000_000_000) } catch { return }
                if UIApplication.shared.applicationState == .active && playback.contentGate == nil && playback.phase != 6 && playback.phase != 7 { services.refreshPlayerInfo() }
            }
        }
    }
}

// This controller owns only the theatre presentation. Twitch's application,
// scene delegate, authentication coordinator and guarded root remain intact.
private final class PortraitTheatreController: UIHostingController<TheatreContent> {
    override var supportedInterfaceOrientations: UIInterfaceOrientationMask { .portrait }
    override var preferredInterfaceOrientationForPresentation: UIInterfaceOrientation { .portrait }
    override var shouldAutorotate: Bool { false }
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        setNeedsUpdateOfSupportedInterfaceOrientations()
        view.window?.windowScene?.requestGeometryUpdate(.iOS(interfaceOrientations: .portrait))
    }
}

@MainActor
enum NativeTheatre {
    static func controller(channel: FollowedChannel, services: NativeServices, playback: TheatrePlayback? = nil, close: @escaping () -> Void) -> UIViewController {
        let owned = playback ?? TheatrePlayback(channel: channel.username)
        let account = services.state.account
        owned.bindContentOwner(valid: {
            UIApplication.shared.applicationState == .active && SSNNavigationPermitted() &&
            services.state.session == .authenticated && services.state.account == account
        }, close: close)
        if playback == nil { services.prepareContentGate(channel, playback: owned) }
        let controller = PortraitTheatreController(rootView: TheatreContent(channel: channel, services: services, playback: owned, close: close))
        controller.modalPresentationStyle = .fullScreen
        return controller
    }
}
