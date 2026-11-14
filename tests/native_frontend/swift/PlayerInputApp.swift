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

// Bounded render-time observations, confined to this synthetic fixture.
// No SwiftUI state is mutated by an interpolated modifier evaluation.
private final class MotionFrameSamples {
    private let lock = NSLock()
    private var expected: PlayerControlAnimation?
    private var entering = true
    private var edges = 0, center = 0, samples = 0
    private var minimum = 1.0, maximum = 0.0
    private var earlyCenterHidden = false, lateEdgesSettled = false, invalid = false
    private var previous: Double?
    func begin(style: PlayerControlAnimation, entering: Bool) {
        lock.lock(); defer { lock.unlock() }
        expected = style; self.entering = entering
        edges = 0; center = 0; samples = 0; minimum = 1; maximum = 0
        earlyCenterHidden = false; lateEdgesSettled = false; invalid = false; previous = nil
    }
    func record(style: PlayerControlAnimation, region: PlayerControlRegion, progress: Double, frame: PlayerControlFrame) {
        lock.lock(); defer { lock.unlock() }
        guard let expected, progress > 0.001, progress < 0.999,
              region == .topTrailing || region == .center, samples < 512 else { return }
        samples += 1; invalid = invalid || style != expected
        minimum = min(minimum, progress); maximum = max(maximum, progress)
        if region == .topTrailing {
            if let previous {
                invalid = invalid || (entering ? progress < previous - 0.03 : progress > previous + 0.03)
            }
            previous = progress
            let distance = abs(frame.x) + abs(frame.y)
            if style == .fade {
                if frame.opacity > 0.01 && frame.opacity < 0.99 { edges += 1 }
                invalid = invalid || distance > 0.001
            } else {
                if distance > 1 && progress > 0.05 { edges += 1 }
                if progress > 0.75 && distance < 0.001 { lateEdgesSettled = true }
            }
        } else {
            invalid = invalid || abs(frame.x) + abs(frame.y) > 0.001
            if frame.opacity > 0.01 && frame.opacity < 0.99 { center += 1 }
            if style != .fade && progress < 0.6 {
                earlyCenterHidden = true
                invalid = invalid || frame.opacity > 0.001
            }
        }
    }
    func finish() -> (Bool, String) {
        lock.lock(); defer { lock.unlock() }
        let sequenced = expected == .fade || (earlyCenterHidden && lateEdgesSettled)
        let passed = !invalid && edges >= 2 && center >= 2 && minimum < 0.25 && maximum > 0.8 && sequenced
        let detail = "\(expected?.rawValue ?? "missing") \(entering ? "in" : "out"): edges=\(edges), center=\(center), sequenced=\(sequenced), invalid=\(invalid)"
        expected = nil
        return (passed, detail)
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
    @State private var motionSamples = MotionFrameSamples()
    @State private var motionVisible: Bool?
    @State private var motionReduceMotion: Bool?
    @State private var motionResult = "Not checked"
    @State private var motionDetails = ""
    @State private var checkingMotion = false
    @State private var copied = "Not copied"
    private var channel: FollowedChannel {
        var c = FollowedChannel(username: "fixture_channel", displayName: "Fixture")
        c.isLive = true; c.title = "Synthetic interaction fixture"; c.viewerCount = 123; c.startedAt = Date().addingTimeInterval(-3600)
        return c
    }
    private func interact() { visibility.reveal(now: ProcessInfo.processInfo.systemUptime) }
    @MainActor private func checkMotion() async {
        guard !checkingMotion else { return }
        checkingMotion = true; motionResult = "Checking"
        let saved = storedAnimation
        defer {
            storedAnimation = saved; motionVisible = nil; motionReduceMotion = nil; checkingMotion = false
        }
        var details: [String] = []
        do {
            // Final cycle verifies that a saved fly mode becomes a nonmoving
            // fade when the fixture supplies the Reduce Motion preference input.
            for (style, reduced) in [(PlayerControlAnimation.vertical, false), (.horizontal, false), (.fade, false), (.vertical, true)] {
                motionVisible = false
                try await Task.sleep(nanoseconds: 800_000_000)
                storedAnimation = style.rawValue; motionReduceMotion = reduced
                try await Task.sleep(nanoseconds: 100_000_000)
                for entering in [true, false] {
                    motionSamples.begin(style: reduced ? .fade : style, entering: entering)
                    motionVisible = entering
                    try await Task.sleep(nanoseconds: 800_000_000)
                    let (passed, detail) = motionSamples.finish()
                    details.append(detail)
                    guard passed else { motionResult = "Failed"; motionDetails = details.joined(separator: "; "); return }
                }
            }
            motionDetails = details.joined(separator: "; "); motionResult = "Passed"
        } catch { motionResult = "Failed"; motionDetails = "Sampling cancelled" }
    }
    var body: some View {
        VStack {
            if closed { Text("Closed").accessibilityIdentifier("closed") }
            else {
                PlayerCanvas(surface: media, toggleControls: { visibility.toggle(now: ProcessInfo.processInfo.systemUptime) }) {
                    PlayerControls(visible: motionVisible ?? visibility.visible, channel: channel, clock: clock, paused: paused, muted: muted,
                                   close: { closed = true }, pause: { paused.toggle() }, mute: { muted.toggle() },
                                   interact: interact, presentationChanged: { presenting = $0 },
                                   motionSample: { motionSamples.record(style: $0, region: $1, progress: $2, frame: $3) },
                                   motionReductionOverride: motionReduceMotion)
                }
            }
            Button("Next animation") {
                let styles = PlayerControlAnimation.allCases
                let current = styles.firstIndex(of: PlayerControlAnimation(rawValue: storedAnimation) ?? .vertical) ?? 0
                storedAnimation = styles[(current + 1) % styles.count].rawValue
                interact()
            }.accessibilityIdentifier("next-animation")
            Text(storedAnimation).accessibilityIdentifier("animation-style")
            Button("Check animation frames") { Task { await checkMotion() } }
                .disabled(checkingMotion).accessibilityIdentifier("motion-checks")
            Text(motionResult).accessibilityIdentifier("motion-check-result").accessibilityValue(motionDetails)
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
