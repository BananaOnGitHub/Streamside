import SwiftUI
import UIKit

@MainActor
private final class TheatrePlayback: ObservableObject {
    let native: SSNPlayback
    @Published private(set) var phase = 0
    @Published private(set) var error = 0
    @Published private(set) var paused = false
    @Published private(set) var muted = false
    init(channel: String) { native = SSNPlayback(channel: channel) }
    func start() { native.start(); update() }
    func stop() { native.stop(); update() }
    func togglePaused() { native.isPaused.toggle(); update() }
    func toggleMuted() { native.isMuted.toggle(); update() }
    func update() {
        if paused != native.isPaused { paused = native.isPaused }
        if muted != native.isMuted { muted = native.isMuted }
        if phase != native.phase { phase = native.phase }
        if error != native.errorCode { error = native.errorCode }
    }
    var message: String {
        switch phase {
        case 1: return "Requesting stream access…"
        case 2: return "Loading live video…"
        case 3: return "Live"
        case 4: return "Buffering…"
        case 5: return "Playback paused while the app is inactive"
        case 8: return "Paused"
        case 6: return "This stream has ended"
        case 7:
            switch error {
            case 1: return "Your session changed. Return to your followed channels."
            case 2, 3: return "Native playback is unavailable. Export diagnostics."
            case 4: return "Twitch could not authorize this stream. It may be offline or restricted."
            case 5: return "Audio could not start. Try again."
            case 6: return "The stream took too long to load. Try again."
            default: return "The player could not open this stream. Try again or export diagnostics."
            }
        default: return "Playback stopped"
        }
    }
}

private struct TheatreContent: View {
    let channel: FollowedChannel
    @ObservedObject var services: NativeServices
    let close: () -> Void
    @StateObject private var playback: TheatrePlayback
    @State private var controls = PlayerControlsVisibility()
    @State private var overlayPresented = false
    @State private var voiceOver = UIAccessibility.isVoiceOverRunning
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private var currentChannel: FollowedChannel {
        services.state.channels.first { $0.id == channel.id } ?? channel
    }
    private func interact() { controls.reveal(now: ProcessInfo.processInfo.systemUptime) }
    init(channel: FollowedChannel, services: NativeServices, close: @escaping () -> Void) {
        self.channel = channel; self.services = services; self.close = close
        _playback = StateObject(wrappedValue: TheatrePlayback(channel: channel.username))
    }
    var body: some View {
        VStack(spacing: 0) {
            PlayerCanvas(surface: playback.native.view, toggleControls: {
                SSNPlayerControlEvent(0)
                controls.toggle(now: ProcessInfo.processInfo.systemUptime)
            }) {
                PlayerControls(channel: currentChannel, clock: services.clock,
                               paused: playback.paused, muted: playback.muted,
                               close: { playback.stop(); close() }, pause: playback.togglePaused,
                               mute: playback.toggleMuted, interact: interact,
                               presentationChanged: { overlayPresented = $0 })
                    .opacity(controls.visible ? 1 : 0)
                    .allowsHitTesting(controls.visible)
                    .accessibilityHidden(!controls.visible)
                    .animation(reduceMotion ? nil : .easeInOut(duration: 0.16), value: controls.visible)
            }
            VStack(alignment: .leading, spacing: 8) {
                Text(currentChannel.displayName).font(.headline)
                Text(currentChannel.title).font(.subheadline).lineLimit(2)
                HStack {
                    if playback.phase == 1 || playback.phase == 2 || playback.phase == 4 { ProgressView() }
                    Text(playback.message).font(.footnote).foregroundStyle(.secondary)
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
        .onAppear { playback.start(); interact() }
        .onDisappear { playback.stop() }
        .task {
            while !Task.isCancelled {
                playback.update()
                controls.tick(now: ProcessInfo.processInfo.systemUptime,
                              keepVisible: overlayPresented || voiceOver)
                do { try await Task.sleep(nanoseconds: 250_000_000) } catch { return }
            }
        }
        .onChange(of: services.state.session) { session in
            if session != .authenticated { playback.stop(); close() }
        }
        .onReceive(NotificationCenter.default.publisher(for: UIAccessibility.voiceOverStatusDidChangeNotification)) { _ in
            voiceOver = UIAccessibility.isVoiceOverRunning; interact()
        }
        .task {
            // Reuse the authenticated native account/feed client, with its request
            // guard. Do not reload thumbnails or poll when the app is inactive.
            while !Task.isCancelled {
                do { try await Task.sleep(nanoseconds: 30_000_000_000) } catch { return }
                if UIApplication.shared.applicationState == .active && playback.phase != 6 && playback.phase != 7 { services.refreshPlayerInfo() }
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
    static func controller(channel: FollowedChannel, services: NativeServices, close: @escaping () -> Void) -> UIViewController {
        let controller = PortraitTheatreController(rootView: TheatreContent(channel: channel, services: services, close: close))
        controller.modalPresentationStyle = .fullScreen
        return controller
    }
}
