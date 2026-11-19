import Foundation

// Only the Objective-C media boundary is synthetic. Execute the production
// TheatrePlayback and MarkedContentGate state/ownership with no Apple video SDK.
@MainActor final class SSNPlayback {
    static var creations = 0
    var phase = 0, errorCode = 0
    var isPaused = false, isMuted: Bool
    private(set) var starts = 0
    init(channel: String, preview: Bool = false) { Self.creations += 1; isMuted = preview }
    func start() { starts += 1; phase = 3 }
    func stop() { phase = 0 }
    func enterTheatre() -> Bool { true }
}
@main struct PlaybackAdmissionTests {
    @MainActor static func wait(_ gate: MarkedContentGate) async {
        for _ in 0..<1000 where gate.stage == .loading {
            try? await Task.sleep(nanoseconds: 1_000_000)
        }
        precondition(gate.stage != .loading, "Synthetic label result never resolved")
    }
    @MainActor static func main() async {
        for remember in [false, true] {
            let playback = TheatrePlayback(channel: "fixture", preview: true)
            var loads = 0, warnings = true, thumbnails = false, closes = 0
            playback.bindContentOwner(valid: { true }, close: { closes += 1 })
            playback.configureContentGate { completion in
                MarkedContentGate(load: { loads += 1; return ["Fixture label"] }, valid: { playback.contentIsValid },
                    saveWarnings: { warnings = $0 }, saveThumbnails: { thumbnails = $0 }, completion: completion)
            }
            let gate = playback.contentGate!
            playback.start(); playback.startIfNeeded(); playback.start()
            await wait(gate)
            precondition(loads == 1 && playback.native!.starts == 0 && gate.stage == .warning)
            gate.dontShowAgain = remember
            if remember {
                // A pending Watch rebinds the same facade/gate to a new owner.
                let identity = ObjectIdentifier(playback.native!)
                playback.bindContentOwner(valid: { true }, close: { closes += 10 })
                playback.enterTheatre(); playback.startIfNeeded()
                precondition(playback.native!.starts == 0 && !playback.muted && playback.contentGate === gate)
                gate.proceed()
                precondition(!warnings && !thumbnails && playback.native!.starts == 0 && gate.stage == .thumbnails)
                gate.chooseThumbnails(true)
                precondition(thumbnails && playback.contentGate == nil && playback.native!.starts == 1 && ObjectIdentifier(playback.native!) == identity)
                playback.startIfNeeded(); precondition(playback.native!.starts == 1 && closes == 0)
            } else {
                gate.dontShowAgain = true; gate.close()
                precondition(closes == 1 && warnings && !thumbnails && playback.native!.starts == 0)
                playback.startIfNeeded(); precondition(playback.native!.starts == 0 && closes == 1, "Cancelled appearance must not dismiss twice")
            }
            playback.stop()
        }
        let beforeLocal = SSNPlayback.creations
        for status in LocalTestStream.Status.allCases {
            var draft = LocalTestStream(); draft.status = status
            let local = TheatrePlayback(channel: "a_real_twitch_name", preview: true, localTest: draft)
            var allowed = true
            local.bindContentOwner(valid: { allowed }, close: {})
            local.configureContentGate { completion in
                MarkedContentGate(load: { draft.contentLabels }, valid: { allowed },
                    saveWarnings: { _ in }, saveThumbnails: { _ in }, completion: completion)
            }
            local.start(); await wait(local.contentGate!)
            precondition(local.native == nil && local.phase == 0)
            local.contentGate!.proceed()
            precondition(local.phase == (DevelopmentTools.enabled ? status.phase : 7) && local.muted)
            local.enterTheatre(); local.setMuted(false); local.togglePaused(); local.toggleMuted()
            precondition(local.native == nil && local.muted)
            allowed = false; local.stop(); local.startIfNeeded(); precondition(local.phase == 0)
        }
        precondition(SSNPlayback.creations == beforeLocal, "Local testing must never instantiate the donor playback facade")
        let cancelled = TheatrePlayback(channel: "fixture", preview: true)
        var valid = true, closes = 0
        cancelled.bindContentOwner(valid: { valid }, close: { closes += 1 })
        cancelled.configureContentGate { completion in
            MarkedContentGate(load: {
                try? await Task.sleep(nanoseconds: 20_000_000); return ["Late fixture label"]
            }, valid: { valid }, saveWarnings: { _ in fatalError("Cancelled preferences") }, saveThumbnails: { _ in fatalError("Cancelled thumbnails") }, completion: completion)
        }
        let gate = cancelled.contentGate!
        cancelled.start(); valid = false; cancelled.stop(); gate.proceed()
        try? await Task.sleep(nanoseconds: 30_000_000)
        precondition(cancelled.native!.starts == 0 && cancelled.contentGate == nil && closes == 0)
        let reowned = TheatrePlayback(channel: "fixture", preview: true)
        reowned.bindContentOwner(valid: { true }, close: { closes += 1 })
        reowned.configureContentGate { completion in
            MarkedContentGate(load: { ["Label"] }, valid: { true }, saveWarnings: { _ in }, saveThumbnails: { _ in }, completion: completion)
        }
        reowned.start(); await wait(reowned.contentGate!)
        reowned.bindContentOwner(valid: { true }, close: { closes += 10 })
        reowned.contentGate?.close()
        precondition(closes == 10 && reowned.native!.starts == 0, "Pending Close must use the current theatre owner")
        print("INLINE_ADMISSION PASS: deferred media; one label request; discard-on-close; same-facade Watch; thumbnail choice before start; cancelled late result; rebound Close")
    }
}
