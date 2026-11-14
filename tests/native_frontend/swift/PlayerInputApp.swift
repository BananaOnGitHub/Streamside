import SwiftUI
import UIKit

// Only the control's bounded diagnostic callback is stubbed. Production views,
// hit regions, video wrapper, popovers, URL copy/share and visibility are reused.
func SSNPlayerControlEvent(_ event: UInt32) {}

private final class InputHungryVideo: UIView {
    var changedRenderer = false { didSet { invalidateIntrinsicContentSize(); setNeedsLayout() } }
    override var intrinsicContentSize: CGSize { changedRenderer ? CGSize(width: 4096, height: 2160) : CGSize(width: 1080, height: 1920) }
    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        fatalError("A display-only media surface received an input event")
    }
    override func layoutSubviews() {
        super.layoutSubviews()
        // A renderer changing aspect must not change the external input canvas.
        backgroundColor = changedRenderer ? .systemPurple : .systemIndigo
    }
}

private struct InputTestContent: View {
    @State private var media = InputHungryVideo()
    @StateObject private var clock = StreamClock()
    @State private var visibility = PlayerControlsVisibility()
    @State private var presenting = false
    @State private var holdOpen = true
    @State private var paused = false
    @State private var muted = false
    @State private var closed = false
    @AppStorage(PlayerPreferences.animationKey) private var storedAnimation = PlayerControlAnimation.vertical.rawValue
    @State private var copied = "Not copied"
    private var channel: FollowedChannel {
        var c = FollowedChannel(username: "fixture_channel", displayName: "Fixture")
        c.isLive = true; c.title = "Synthetic interaction fixture"; c.viewerCount = 123; c.startedAt = Date().addingTimeInterval(-3600)
        return c
    }
    private func interact() { visibility.reveal(now: ProcessInfo.processInfo.systemUptime) }
    var body: some View {
        VStack {
            if closed { Text("Closed").accessibilityIdentifier("closed") }
            else {
                PlayerCanvas(surface: media, toggleControls: { visibility.toggle(now: ProcessInfo.processInfo.systemUptime) }) {
                    PlayerControls(visible: visibility.visible, channel: channel, clock: clock, paused: paused, muted: muted,
                                   close: { closed = true }, pause: { paused.toggle() }, mute: { muted.toggle() },
                                   interact: interact, presentationChanged: { presenting = $0 })
                }
            }
            Button("Next animation") {
                let styles = PlayerControlAnimation.allCases
                let current = styles.firstIndex(of: PlayerControlAnimation(rawValue: storedAnimation) ?? .vertical) ?? 0
                storedAnimation = styles[(current + 1) % styles.count].rawValue
                interact()
            }.accessibilityIdentifier("next-animation")
            Text(storedAnimation).accessibilityIdentifier("animation-style")
            Text("Harness").accessibilityIdentifier("harness-title")
            Toggle("Hold controls open", isOn: $holdOpen).accessibilityIdentifier("hold-controls")
            Button("Change renderer") { media.changedRenderer.toggle(); interact() }.accessibilityIdentifier("resize")
            Button("Clear clipboard") { UIPasteboard.general.items = [] }.accessibilityIdentifier("clear-clipboard")
            Button("Read clipboard") { copied = UIPasteboard.general.url?.absoluteString ?? "Missing URL" }.accessibilityIdentifier("read-clipboard")
            Text(copied).accessibilityIdentifier("copied-link")
            Text(verbatim: "hold=\(holdOpen) popup=\(presenting) visible=\(visibility.visible)")
                .font(.caption).accessibilityIdentifier("fixture-state")
            Spacer()
        }
        .onAppear { interact() }
        .onChange(of: holdOpen) { if $0 { interact() } }
        .task {
            while !Task.isCancelled {
                visibility.tick(now: ProcessInfo.processInfo.systemUptime, keepVisible: (holdOpen && visibility.visible) || presenting)
                try? await Task.sleep(nanoseconds: 100_000_000)
            }
        }
    }
}
@main @MainActor final class InputTestDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ app: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UserDefaults.standard.set(!ProcessInfo.processInfo.arguments.contains("--plain"), forKey: PlayerPreferences.glassButtonsKey)
        UserDefaults.standard.set(PlayerControlAnimation.vertical.rawValue, forKey: PlayerPreferences.animationKey)
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = UIHostingController(rootView: InputTestContent())
        window.makeKeyAndVisible(); self.window = window; return true
    }
}
