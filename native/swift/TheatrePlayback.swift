import Combine
import Foundation

@MainActor
final class TheatrePlayback: ObservableObject {
    let native: SSNPlayback?
    let localTest: LocalTestStream?
    @Published private(set) var contentGate: MarkedContentGate?
    @Published private(set) var qualities: [String] = []
    @Published private(set) var preferredQuality = "auto"
    @Published private(set) var effectiveQuality = "auto"
    private let channelName: String
    private let qualityPreferences: StreamQualityPreferences
    private var requested = false
    private var cancelled = false
    private var contentValid: () -> Bool = { true }
    private var contentClose: () -> Void = {}
    // Rebind navigation ownership during the same-player preview handoff. A
    // pending warning moves with the facade, without starting media or audio.
    func bindContentOwner(valid: @escaping () -> Bool, close: @escaping () -> Void) {
        contentValid = valid; contentClose = close
    }
    func configureContentGate(_ make: (@escaping (Bool) -> Void) -> MarkedContentGate?) {
        guard !requested, !cancelled, contentGate == nil else { return }
        contentGate = make { [weak self] accepted in
            guard let self, !self.cancelled else { return }
            guard accepted, self.contentValid() else {
                self.stop(); self.contentClose(); return
            }
            self.contentGate = nil
            if self.requested { self.start() }
        }
    }
    var contentIsValid: Bool { !cancelled && contentValid() }
    @Published private(set) var phase = 0
    @Published private(set) var error = 0
    @Published private(set) var paused = false
    @Published private(set) var muted = false
    init(channel: String, preview: Bool = false, localTest: LocalTestStream? = nil, qualityDefaults: UserDefaults = .standard) {
        self.localTest = localTest; channelName = channel
        qualityPreferences = StreamQualityPreferences(defaults: qualityDefaults)
        // Fail closed for a local origin even in builds where tools are disabled.
        native = localTest == nil ? SSNPlayback(channel: channel, preview: preview) : nil
        muted = preview
        if localTest == nil {
            preferredQuality = qualityPreferences.selection(for: channel)
            native?.preferredQuality = preferredQuality
        }
    }
    func selectQuality(_ name: String) {
        guard let native, !cancelled, contentIsValid, name == "auto" || qualities.contains(name) else { return }
        native.preferredQuality = name
        qualityPreferences.save(name, for: channelName)
        update()
    }
    func enterTheatre() {
        guard contentIsValid else { return }
        if localTest != nil { muted = true; return }
        if native?.enterTheatre() == true { native?.isMuted = false }
        update()
    }
    func start() {
        guard !cancelled else { return }
        guard contentValid() else { stop(); contentClose(); return }
        if let contentGate {
            if !requested { requested = true; contentGate.start() }
            return
        }
        requested = true
        if let localTest {
            phase = DevelopmentTools.enabled ? localTest.status.phase : 7
            error = DevelopmentTools.enabled ? 0 : 2; muted = true
            return
        }
        native?.start(); update()
    }
    func startIfNeeded() { if !cancelled && !requested && phase == 0 { start() } }
    func setMuted(_ muted: Bool) { if localTest != nil { self.muted = true; return }; native?.isMuted = muted; update() }
    func stop() {
        cancelled = true; requested = false
        let gate = contentGate; contentGate = nil; gate?.close()
        if localTest != nil { phase = 0; return }
        native?.stop(); update()
    }
    func togglePaused() { guard let native else { return }; native.isPaused.toggle(); update() }
    func toggleMuted() { guard let native else { return }; native.isMuted.toggle(); update() }
    func update() {
        guard let native else { return }
        if qualities != native.qualities { qualities = native.qualities }
        if preferredQuality != native.preferredQuality { preferredQuality = native.preferredQuality }
        if effectiveQuality != native.effectiveQuality { effectiveQuality = native.effectiveQuality }
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
