import Combine
import Foundation

@MainActor
final class TheatrePlayback: ObservableObject {
    let native: SSNPlayback
    @Published private(set) var contentGate: MarkedContentGate?
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
    init(channel: String, preview: Bool = false) { native = SSNPlayback(channel: channel, preview: preview) }
    func enterTheatre() {
        guard contentIsValid else { return }
        if native.enterTheatre() { native.isMuted = false }
        update()
    }
    func start() {
        guard !cancelled else { return }
        guard contentValid() else { stop(); contentClose(); return }
        if let contentGate {
            if !requested { requested = true; contentGate.start() }
            return
        }
        requested = true; native.start(); update()
    }
    func startIfNeeded() { if !cancelled && !requested && phase == 0 { start() } }
    func setMuted(_ muted: Bool) { native.isMuted = muted; update() }
    func stop() {
        cancelled = true; requested = false
        let gate = contentGate; contentGate = nil; gate?.close()
        native.stop(); update()
    }
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
