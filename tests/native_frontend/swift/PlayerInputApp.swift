import SwiftUI
import UIKit

// Only the control's bounded diagnostic callback is stubbed. Production views,
// hit regions, video wrapper, popovers, URL copy/share and visibility are reused.
func SSNPlayerControlEvent(_ event: UInt32) {}
func ssn_adblock_set_enabled(_ enabled: Bool) {}

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
    private var midCenterFading = false, midEdgesMoving = false, invalid = false
    private var previous: [PlayerControlRegion: Double] = [:]
    private var edgeRegions: [PlayerControlRegion: Int] = [:]
    private var earlyRegions = Set<PlayerControlRegion>()
    private var sharedTravel: CGSize?
    private var latest = "No modifier frames"
    private var centerFrames = RenderedFrameDirection()
    func begin(style: PlayerControlAnimation, entering: Bool) {
        lock.lock(); defer { lock.unlock() }
        expected = style; self.entering = entering
        edges = 0; center = 0; samples = 0; minimum = 1; maximum = 0
        midCenterFading = false; midEdgesMoving = false; invalid = false; previous = [:]; edgeRegions = [:]; earlyRegions = []; sharedTravel = nil
    }
    func record(style: PlayerControlAnimation, region: PlayerControlRegion, progress: Double, travel: CGSize, frame: PlayerControlFrame) {
        lock.lock(); defer { lock.unlock() }
        if region == .center {
            latest = "progress=\(progress), alpha=\(frame.opacity)"
            centerFrames.record(style: style, progress: progress)
        }
        guard let expected, progress > 0.001, progress < 0.999,
              region != .shade, samples < 2048 else { return }
        samples += 1; invalid = invalid || style != expected
        minimum = min(minimum, progress); maximum = max(maximum, progress)
        if region != .center {
            // Matching normalized progress alone permits different speeds.
            // Require identical absolute travel for all edges throughout a stage.
            if let sharedTravel { invalid = invalid || travel != sharedTravel }
            else { sharedTravel = travel }
            if let old = previous[region] {
                invalid = invalid || (entering ? progress < old - 0.03 : progress > old + 0.03)
            }
            previous[region] = progress
            edgeRegions[region, default: 0] += 1
            let distance = abs(frame.x) + abs(frame.y)
            if style == .fade {
                if frame.opacity > 0.01 && frame.opacity < 0.99 { edges += 1 }
                invalid = invalid || distance > 0.001
            } else {
                if distance > 1 && progress > 0.05 { edges += 1 }
                if progress > 0.25 && progress < 0.75 && distance > 1 { midEdgesMoving = true }
                let extent = style == .horizontal ? Double(travel.width) : Double(travel.height)
                let alpha = PlayerControlMotion.frame(progress: progress, style: style, region: .center, width: 1, height: 1).opacity
                invalid = invalid || extent <= 0 || abs(distance / max(1, extent) + alpha - 1) > 0.000001
                if progress > 0.05 && progress < 0.2 && alpha > 0.14 { earlyRegions.insert(region) }
            }
        } else {
            invalid = invalid || abs(frame.x) + abs(frame.y) > 0.001
            if frame.opacity > 0.01 && frame.opacity < 0.99 { center += 1 }
            // Fade must occupy the same complete timeline as edge travel.
            let expectedAlpha = PlayerControlMotion.frame(progress: progress, style: style, region: .shade, width: 1, height: 1).opacity
            invalid = invalid || abs(frame.opacity - expectedAlpha) > 0.000001
            if progress > 0.25 && progress < 0.75 && frame.opacity > 0.01 && frame.opacity < 0.99 {
                midCenterFading = true
            }
        }
    }
    func renderedCenter() -> (sequence: UInt64, style: PlayerControlAnimation, progress: Double, previous: Double)? {
        lock.lock(); defer { lock.unlock() }
        return centerFrames.latest
    }
    func lastFrame() -> String {
        lock.lock(); defer { lock.unlock() }
        return latest
    }
    private var coversRange: Bool { minimum < 0.25 && maximum > 0.8 }

    func sampledRange() -> (covered: Bool, detail: String) {
        lock.lock(); defer { lock.unlock() }
        return (coversRange, String(format: "range=%.3f...%.3f", minimum, maximum))
    }

    func finish() -> (Bool, String) {
        lock.lock(); defer { lock.unlock() }
        let allEdges = edgeRegions.count == 4 && edgeRegions.values.allSatisfy { $0 >= 2 }
        let synchronized = sharedTravel != nil && allEdges && midCenterFading && (expected == .fade || (midEdgesMoving && earlyRegions.count == 4))
        let passed = !invalid && edges >= 2 && center >= 2 && coversRange && synchronized
        let range = String(format: "%.3f...%.3f", minimum, maximum)
        let detail = "range=\(range), \(expected?.rawValue ?? "missing") \(entering ? "in" : "out"): sharedTravel=\(sharedTravel.map { "\(Int($0.width))x\(Int($0.height))" } ?? "missing"), edgeRegions=\(edgeRegions.count), earlyRegions=\(earlyRegions.count), edges=\(edges), center=\(center), synchronized=\(synchronized), invalid=\(invalid)"
        expected = nil
        return (passed, detail)
    }
}

// Actual onscreen snapshots of this owned fixture, never donor/account content.
@MainActor private enum OpacityPixelCheck {
    static func snapshot(_ window: UIWindow) -> CGImage? {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1; format.opaque = true
        var complete = false
        let image = UIGraphicsImageRenderer(size: window.bounds.size, format: format).image { _ in
            complete = window.drawHierarchy(in: window.bounds, afterScreenUpdates: false)
        }
        return complete ? image.cgImage : nil
    }
    private static func rgba(_ image: CGImage, region: CGRect) -> [UInt8]? {
        let rect = region.integral
        guard CGRect(x: 0, y: 0, width: CGFloat(image.width), height: CGFloat(image.height)).contains(rect),
              let crop = image.cropping(to: rect) else { return nil }
        let width = crop.width, height = crop.height
        var bytes = [UInt8](repeating: 0, count: width * height * 4)
        let drawn = bytes.withUnsafeMutableBytes { buffer -> Bool in
            guard let context = CGContext(data: buffer.baseAddress, width: width, height: height,
                                          bitsPerComponent: 8, bytesPerRow: width * 4,
                                          space: CGColorSpaceCreateDeviceRGB(),
                                          bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue) else { return false }
            context.draw(crop, in: CGRect(x: 0, y: 0, width: CGFloat(width), height: CGFloat(height)))
            return true
        }
        return drawn ? bytes : nil
    }
    static func evaluate(hidden: CGImage, shown: CGImage, partial: CGImage, canvas: CGRect) -> (Bool, String) {
        let regions = [("center", CGRect(x: canvas.midX - 22, y: canvas.midY - 22, width: 44, height: 44)),
                       ("actions", CGRect(x: canvas.maxX - 188, y: canvas.minY + 6, width: 182, height: 44)),
                       ("audio", CGRect(x: canvas.maxX - 96, y: canvas.maxY - 50, width: 90, height: 44))]
        var details: [String] = []
        var passed = true
        for (name, rect) in regions {
            guard let a = rgba(hidden, region: rect), let b = rgba(shown, region: rect),
                  let m = rgba(partial, region: rect), a.count == b.count, a.count == m.count else { return (false, "Invalid snapshot region: " + name) }
            var numerator = 0.0, denominator = 0.0, count = 0
            for index in stride(from: 0, to: a.count, by: 4) {
                // Ignore the subtle video shade; require contrast from actual
                // glyph/material pixels, measured against hidden/shown endpoints.
                let contrast = (0..<3).map { abs(Int(b[index + $0]) - Int(a[index + $0])) }.max() ?? 0
                guard contrast >= 64 else { continue }
                count += 1
                for channel in 0..<3 {
                    let delta = Double(b[index + channel]) - Double(a[index + channel])
                    numerator += (Double(m[index + channel]) - Double(a[index + channel])) * delta
                    denominator += delta * delta
                }
            }
            let ratio = denominator > 0 ? numerator / denominator : -1
            passed = passed && count >= 20 && ratio > 0.15 && ratio < 0.85
            details.append(name + " ratio=" + String(format: "%.3f", ratio) + " pixels=\(count)")
        }
        return (passed, details.joined(separator: ", "))
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
    @State private var resolution = "auto"
    @State private var closed = false
    @AppStorage(PlayerPreferences.animationKey) private var storedAnimation = PlayerControlAnimation.vertical.rawValue
    @State private var motionSamples = MotionFrameSamples()
    @State private var motionVisible: Bool?
    @State private var motionDurationScale = 1.0
    @State private var motionReduceMotion: Bool?
    @State private var motionResult = "Not checked"
    @State private var motionDetails = ""
    @State private var checkingMotion = false
    @State private var pixelResult = "Not checked"
    @State private var pixelDetails = ""
    @State private var copied = "Not copied"
    private var channel: FollowedChannel {
        var c = FollowedChannel(username: "fixture_channel", displayName: "Fixture")
        c.isLive = true; c.title = "Synthetic interaction fixture"; c.viewerCount = 123; c.startedAt = Date().addingTimeInterval(-3600)
        return c
    }
    private func interact() { visibility.reveal(now: ProcessInfo.processInfo.systemUptime) }
    @MainActor private func partialOpacitySnapshot(_ window: UIWindow, after sequence: UInt64, entering: Bool) async throws -> (CGImage?, String) {
        // Observe the actual production modifier's rendered phase, rather than
        // sleeping half a duration from a SwiftUI state assignment. A busy
        // runner can defer that assignment's render/animation transaction.
        let deadline = CACurrentMediaTime() + 3
        while CACurrentMediaTime() < deadline {
            if let frame = motionSamples.renderedCenter(), frame.sequence > sequence,
               frame.style == .fade, frame.progress >= 0.4, frame.progress <= 0.6,
               (entering ? frame.progress > frame.previous : frame.progress < frame.previous) {
                // Let the compositor present this render. Capture exactly once;
                // pixel evidence still has to satisfy the existing thresholds.
                try await Task.sleep(nanoseconds: 20_000_000)
                let image = OpacityPixelCheck.snapshot(window)
                let end = motionSamples.renderedCenter()?.progress ?? -1
                return (image, String(format: "observed %.3f; captured %.3f", frame.progress, end))
            }
            try await Task.sleep(nanoseconds: 8_000_000)
        }
        return (nil, "No directional intermediate rendered fade frame within 3s")
    }
    @MainActor private func checkOpacityPixels() async throws -> Bool {
        pixelResult = "Checking"
        guard let window = (UIApplication.shared.delegate as? InputTestDelegate)?.window else {
            pixelDetails = "Missing owned window"; pixelResult = "Failed"; return false
        }
        let canvas = media.convert(media.bounds, to: window)
        guard canvas.width > 200, canvas.height > 100 else {
            pixelDetails = "Invalid canvas bounds"; pixelResult = "Failed"; return false
        }
        storedAnimation = PlayerControlAnimation.fade.rawValue; motionReduceMotion = false
        motionVisible = false
        try await waitForRenderedEndpoint(0)
        guard let hidden = OpacityPixelCheck.snapshot(window) else {
            pixelDetails = "Incomplete hidden snapshot"; pixelResult = "Failed"; return false
        }
        let entrySequence = motionSamples.renderedCenter()?.sequence ?? 0
        motionVisible = true
        let entryFrame = try await partialOpacitySnapshot(window, after: entrySequence, entering: true)
        guard let entering = entryFrame.0 else {
            pixelDetails = "Incomplete entry snapshot: " + entryFrame.1; pixelResult = "Failed"; return false
        }
        try await waitForRenderedEndpoint(1)
        guard let shown = OpacityPixelCheck.snapshot(window) else {
            pixelDetails = "Incomplete shown snapshot"; pixelResult = "Failed"; return false
        }
        let exitSequence = motionSamples.renderedCenter()?.sequence ?? 0
        motionVisible = false
        let exitFrame = try await partialOpacitySnapshot(window, after: exitSequence, entering: false)
        guard let leaving = exitFrame.0 else {
            pixelDetails = "Incomplete exit snapshot: " + exitFrame.1; pixelResult = "Failed"; return false
        }
        let entry = OpacityPixelCheck.evaluate(hidden: hidden, shown: shown, partial: entering, canvas: canvas)
        let exit = OpacityPixelCheck.evaluate(hidden: hidden, shown: shown, partial: leaving, canvas: canvas)
        pixelDetails = "in (" + entryFrame.1 + "): " + entry.1 + "; out (" + exitFrame.1 + "): " + exit.1
        pixelResult = entry.0 && exit.0 ? "Passed" : "Failed"
        // Settle the preceding exit before returning to normal-speed reversal.
        try await waitForRenderedEndpoint(0)
        return entry.0 && exit.0
    }
    @MainActor private func waitForRenderedEndpoint(_ target: Double, after sequence: UInt64? = nil,
                                                     requireSampledRange: Bool = false) async throws {
        // A model endpoint can be evaluated while its animation still has
        // interpolated values to render. Keep the collector armed until it
        // sees the existing progress range as well as an endpoint.
        let deadline = CACurrentMediaTime() + 5
        var intermediate = sequence == nil
        while CACurrentMediaTime() < deadline {
            if let frame = motionSamples.renderedCenter(), sequence.map({ frame.sequence > $0 }) ?? true {
                if frame.progress > 0.001 && frame.progress < 0.999 { intermediate = true }
                // SwiftUI can evaluate the model endpoint before rendering its
                // intermediate frames. Require an observed transition first.
                if intermediate && abs(frame.progress - target) < 0.001,
                   !requireSampledRange || motionSamples.sampledRange().covered { return }
            }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        let range = requireSampledRange ? "; " + motionSamples.sampledRange().detail : ""
        throw NSError(domain: "MotionEndpoint", code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Rendered endpoint \(target) or required observations missing: " + motionSamples.lastFrame() + range])
    }
    @MainActor private func checkMotion() async {
        guard !checkingMotion else { return }
        checkingMotion = true; motionResult = "Checking"
        motionDurationScale = 3
        let saved = storedAnimation
        defer {
            storedAnimation = saved; motionVisible = nil; motionReduceMotion = nil; motionDurationScale = 1; checkingMotion = false
        }
        var details: [String] = []
        do {
            // Final cycle verifies that a saved fly mode becomes a nonmoving
            // fade when the fixture supplies the Reduce Motion preference input.
            for (style, reduced) in [(PlayerControlAnimation.vertical, false), (.horizontal, false), (.fade, false), (.vertical, true)] {
                if motionVisible != false {
                    let sequence = motionSamples.renderedCenter()?.sequence ?? 0
                    motionVisible = false
                    try await waitForRenderedEndpoint(0, after: sequence)
                } else { try await waitForRenderedEndpoint(0) }
                storedAnimation = style.rawValue; motionReduceMotion = reduced
                try await Task.sleep(nanoseconds: 100_000_000)
                for entering in [true, false] {
                    motionSamples.begin(style: reduced ? .fade : style, entering: entering)
                    let sequence = motionSamples.renderedCenter()?.sequence ?? 0
                    motionVisible = entering
                    try await waitForRenderedEndpoint(entering ? 1 : 0, after: sequence, requireSampledRange: true)
                    let (passed, detail) = motionSamples.finish()
                    details.append(detail)
                    guard passed else { motionResult = "Failed"; motionDetails = details.joined(separator: "; "); return }
                }
            }
            guard try await checkOpacityPixels() else {
                motionDetails = details.joined(separator: "; ") + "; pixels: " + pixelDetails
                motionResult = "Failed"; return
            }
            // Reversal and all subsequent coordinate/auto-hide tests use the
            // normal application duration, independently of slow frame sampling.
            motionDurationScale = 1
            // A stale exit completion must not remove controls after reversal.
            storedAnimation = PlayerControlAnimation.vertical.rawValue; motionReduceMotion = false
            motionVisible = true
            try await Task.sleep(nanoseconds: 160_000_000)
            motionVisible = false
            try await Task.sleep(nanoseconds: 80_000_000)
            motionVisible = true
            try await Task.sleep(nanoseconds: 800_000_000)
            motionDetails = details.joined(separator: "; "); motionResult = "Passed"
        } catch {
            details.append("Sampling failed: " + error.localizedDescription)
            motionDetails = details.joined(separator: "; ")
            motionResult = "Failed"
        }
    }
    var body: some View {
        VStack {
            if closed { Text("Closed").accessibilityIdentifier("closed") }
            else {
                PlayerCanvas(surface: media, toggleControls: { visibility.toggle(now: ProcessInfo.processInfo.systemUptime) }) {
                    PlayerControls(visible: motionVisible ?? visibility.visible, channel: channel, clock: clock, paused: paused, muted: muted,
                                   close: { closed = true }, pause: { paused.toggle() }, mute: { muted.toggle() },
                                   interact: interact, presentationChanged: { presenting = $0 },
                                   qualities: ["720p60", "480p"], preferredQuality: resolution, effectiveQuality: resolution,
                                   selectQuality: { resolution = $0 },
                                   motionSample: { motionSamples.record(style: $0, region: $1, progress: $2, travel: $3, frame: $4) },
                                   motionReductionOverride: motionReduceMotion, motionDurationScale: motionDurationScale)
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
            Text(pixelResult).accessibilityIdentifier("opacity-pixel-result").accessibilityValue(pixelDetails)
            Text("Harness").accessibilityIdentifier("harness-title")
            Toggle("Hold controls open", isOn: $holdOpen).accessibilityIdentifier("hold-controls")
            Button("Change renderer") { media.changedRenderer.toggle(); interact() }.accessibilityIdentifier("resize")
            Button("Clear clipboard") {
                UIPasteboard.general.items = []; copied = "Missing URL"
            }.accessibilityIdentifier("clear-clipboard")
            // Exercise the real general pasteboard through system-authorized
            // paste, rather than synchronously fetching its contents on the UI
            // thread. The URL still comes from production Copy / UIKit Share.
            PasteButton(payloadType: URL.self) { urls in
                copied = urls.first?.absoluteString ?? "Missing URL"
            }.accessibilityIdentifier("read-clipboard")
            Text(copied).accessibilityIdentifier("copied-link")
            Text(resolution).accessibilityIdentifier("resolution-choice")
            Text(verbatim: "hold=\(holdOpen) popup=\(presenting) visible=\(visibility.visible) \(motionSamples.lastFrame())")
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
private struct ChatReadingFixture: View {
    @State private var timeline: TwitchChatTimeline = {
        var initial = TwitchChatTimeline()
        initial.apply(ChatReadingFixture.messages(1...60))
        return initial
    }()
    @State private var latest = 60
    @State private var controlsVisible = true
    @State private var infoProgress = 0.0
    private let channel = FollowedChannel(username: "fixture", displayName: "Fixture channel")
    private let clock = StreamClock()

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 18) {
                Button("Toggle controls") { controlsVisible.toggle() }
                Button("Receive 3 messages") {
                    timeline.apply(Self.messages((latest + 1)...(latest + 3)))
                    latest += 3
                }
            }.padding(8)
            Color.black.frame(height: 150).overlay {
                PlayerControls(visible: controlsVisible, channel: channel, clock: clock, paused: false,
                    muted: false, close: {}, pause: {}, mute: {}, interact: {}, presentationChanged: { _ in },
                    motionTargetChanged: { infoProgress = $0 })
            }
            Text("Fixture stream info").padding(24)
                .modifier(PlayerInfoReveal(progress: infoProgress, style: .vertical))
                .accessibilityHidden(!controlsVisible)
            StreamChatTranscript(timeline: $timeline, statusText: "Waiting for messages…", listening: true)
        }
    }

    nonisolated private static func messages(_ indices: ClosedRange<Int>) -> [TwitchChatEvent] {
        indices.map { index in
            .message(.init(id: String(index), login: "reader", displayName: "Reader", color: 0x00AF99,
                           body: "Message \(index)"))
        }
    }
}

@main @MainActor final class InputTestDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ app: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UserDefaults.standard.set(!ProcessInfo.processInfo.arguments.contains("--plain"), forKey: PlayerPreferences.glassButtonsKey)
        UserDefaults.standard.set(PlayerControlAnimation.vertical.rawValue, forKey: PlayerPreferences.animationKey)
        let window = UIWindow(frame: UIScreen.main.bounds)
        if ProcessInfo.processInfo.arguments.contains("--chat-reading") {
            window.rootViewController = UIHostingController(rootView: ChatReadingFixture())
        } else if ProcessInfo.processInfo.arguments.contains("--profile") {
            window.rootViewController = UIHostingController(rootView: ProfileFixture())
        } else if ProcessInfo.processInfo.arguments.contains("--local-test-editor") {
            window.rootViewController = UIHostingController(rootView: LocalTestEditorFixture())
        } else if ProcessInfo.processInfo.arguments.contains("--marked-content") {
            window.rootViewController = UIHostingController(rootView: MarkedWarningFixture())
        } else if ProcessInfo.processInfo.arguments.contains("--preview-panel") {
            window.rootViewController = UIHostingController(rootView: ContextPreviewFixtureView())
        } else if ProcessInfo.processInfo.arguments.contains("--thumbnail") {
            window.rootViewController = UIHostingController(rootView: ContextPreviewFixtureView())
        } else { window.rootViewController = UIHostingController(rootView: InputTestContent()) }
        window.makeKeyAndVisible(); self.window = window; return true
    }
}
