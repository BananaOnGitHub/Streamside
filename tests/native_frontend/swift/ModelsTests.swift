import Foundation

// Synthetic presentation fixtures. No donor, network or live account is used.
@main struct ModelsTests {
    @MainActor static func contentWarnings() async {
        for marked in [false, true] {
            for show in [false, true] {
                precondition(MarkedContentPreferences.needsWarning(marked: marked, showWarnings: show) == (marked && show))
            }
        }
        for remember in [false, true] {
            var warnings = true, thumbnails = false, completions: [Bool] = []
            let gate = MarkedContentGate(load: { ["Actual native fixture label"] }, valid: { true },
                saveWarnings: { warnings = $0 }, saveThumbnails: { thumbnails = $0 }, completion: { completions.append($0) })
            gate.start()
            for _ in 0..<100 where gate.stage == .loading { await Task.yield() }
            precondition(gate.stage == .warning && gate.labels == ["Actual native fixture label"])
            gate.dontShowAgain = remember; gate.close(); gate.close(); gate.proceed()
            precondition(warnings && !thumbnails && completions == [false], "Close must ignore the checkbox and complete once")
        }
        for remember in [false, true] {
            for showThumbnails in [false, true] {
                var warnings = true, thumbnails = false, completions: [Bool] = []
                let gate = MarkedContentGate(load: { ["Label"] }, valid: { true },
                    saveWarnings: { warnings = $0 }, saveThumbnails: { thumbnails = $0 }, completion: { completions.append($0) })
                gate.start()
                for _ in 0..<100 where gate.stage == .loading { await Task.yield() }
                gate.dontShowAgain = remember; gate.proceed()
                if remember {
                    precondition(!warnings && completions.isEmpty && gate.stage == .thumbnails, "Must choose thumbnails before media admission")
                    gate.chooseThumbnails(showThumbnails)
                    precondition(thumbnails == showThumbnails)
                } else { precondition(warnings && !thumbnails) }
                precondition(completions == [true]); gate.close(); gate.proceed(); precondition(completions == [true])
            }
        }
        for close in [false, true] {
            var thumbnails = false, warnings = true, completions: [Bool] = []
            let gate = MarkedContentGate(load: { ["Label"] }, valid: { true },
                saveWarnings: { warnings = $0 }, saveThumbnails: { _ in fatalError("Existing enabled choice must not be overwritten") },
                thumbnailsEnabled: { thumbnails }, completion: { completions.append($0) })
            gate.start()
            for _ in 0..<100 where gate.stage == .loading { await Task.yield() }
            precondition(gate.stage == .warning && completions.isEmpty)
            // Read the saved setting at Continue, not only when the gate opens.
            thumbnails = true; gate.dontShowAgain = true
            if close { gate.close(); precondition(warnings && completions == [false]) }
            else {
                gate.proceed()
                precondition(!warnings && gate.stage == .finished && completions == [true], "Already-enabled thumbnails must skip the redundant prompt")
            }
            precondition(thumbnails)
        }
        print("PASS: marked thumbnail preference skips redundant prompt and survives Close")
        var valid = true, loaded = false, completed: [Bool] = []
        let cancel = MarkedContentGate(load: {
            try? await Task.sleep(nanoseconds: 20_000_000); loaded = true; return ["Late label"]
        }, valid: { valid }, saveWarnings: { _ in fatalError("Cancellation persisted warnings") },
            saveThumbnails: { _ in fatalError("Cancellation persisted thumbnails") }, completion: { completed.append($0) })
        cancel.start(); await Task.yield(); valid = false; cancel.close()
        try? await Task.sleep(nanoseconds: 30_000_000)
        precondition(cancel.stage == .finished && completed == [false]); _ = loaded
        var attempts = 0
        let retry = MarkedContentGate(load: { attempts += 1; return attempts == 1 ? nil : ["Recovered label"] }, valid: { true },
            saveWarnings: { _ in }, saveThumbnails: { _ in }, completion: { _ in })
        retry.start(); for _ in 0..<100 where retry.stage == .loading { await Task.yield() }
        precondition(retry.stage == .failed)
        retry.start(); for _ in 0..<100 where retry.stage == .loading { await Task.yield() }
        precondition(retry.stage == .warning && attempts == 2); retry.close()
        var admitted: Bool?
        let failure = MarkedContentGate(load: { nil }, valid: { true },
            saveWarnings: { _ in }, saveThumbnails: { _ in }, completion: { admitted = $0 })
        failure.start(); for _ in 0..<100 where failure.stage == .loading { await Task.yield() }
        failure.proceed(); precondition(admitted == false, "Missing labels must not admit playback")
        print("PASS: marked consent, discard-on-close, independent thumbnail choice before playback, failure and cancellation")
    }
    static func repeatedRenderValues() {
        // Reproduce both fade directions with multiple body evaluations at the
        // same rendered value. Duplicates must not erase the last real movement.
        for (start, middle) in [(0.3, 0.5), (0.7, 0.5)] {
            var frames = RenderedFrameDirection()
            frames.record(style: .fade, progress: start)
            frames.record(style: .fade, progress: middle)
            let sequence = frames.latest!.sequence
            for _ in 0..<20 { frames.record(style: .fade, progress: middle) }
            precondition(frames.latest!.progress == middle && frames.latest!.previous == start)
            precondition(frames.latest!.sequence == sequence)
            precondition((frames.latest!.progress > frames.latest!.previous) == (start < middle))
            frames.record(style: .fade, progress: start)
            precondition(frames.latest!.sequence > sequence && frames.latest!.previous == middle)
            frames.record(style: .horizontal, progress: 0.5)
            precondition(frames.latest!.progress == frames.latest!.previous, "A style change is not directional motion")
        }
        print("PASS: duplicate render direction preserved through entry, exit and reversal")
    }
    @MainActor static func localTestData() {
        let name = "dev.streamside.local-models-fixture"
        let defaults = UserDefaults(suiteName: name)!
        defaults.removePersistentDomain(forName: name)
        defer { defaults.removePersistentDomain(forName: name) }
        let store = LocalTestStreamStore(defaults: defaults)
        precondition(store.channel == nil)
        var draft = LocalTestStream(); draft.enabled = true
        draft.username = "an_actual_channel_name"; draft.name = "Edited name"
        draft.title = "Full local title"; draft.category = "Local category"
        draft.tags = "English, Test, Test"; draft.labels = "First label, Second label"
        draft.viewers = -1; draft.status = .loading
        store.save(draft)
        if DevelopmentTools.enabled {
            let channel = store.channel!
            precondition(channel.id == "dev.streamside.local-test" && channel.displayName == "Local test · Edited name")
            precondition(channel.title == draft.title && channel.category == draft.category && channel.viewerCount == 0)
            precondition(channel.avatarURL == nil && channel.thumbnailURL == nil && channel.channelID.isEmpty)
            precondition(channel.localTest?.contentLabels == ["First label", "Second label"] && channel.thumbnailRestricted)
            precondition(LocalTestStreamStore(defaults: defaults).channel == channel, "Local data must restore independently of donor snapshots")
            store.remove(); precondition(store.channel == nil && LocalTestStreamStore(defaults: defaults).channel == nil)
        } else {
            precondition(store.channel == nil && defaults.data(forKey: LocalTestStreamStore.key) == nil,
                "Disabled components cannot persist or materialize local entries")
        }
        let native = FollowedChannel(snapshot: ["username":"real", "isLive":"1", "localTest":true])!
        precondition(native.localTest == nil, "Native snapshots cannot claim local origin")
        print("PASS: local test data, saved metadata, removal, typed origin and development isolation")
    }
    @MainActor static func main() async {
        localTestData()
        repeatedRenderValues()
        await contentWarnings()
        precondition(VerificationStyle.resolve("unknown") == .twitch)
        for style in VerificationStyle.allCases { precondition(VerificationStyle.resolve(style.rawValue) == style) }
        for raw in ["0", "", "true", "partner"] {
            precondition(FollowedChannel(snapshot: ["username":"fixture", "isLive":"1", "isVerified":raw])?.isVerified == false)
        }
        precondition(FollowedChannel(snapshot: ["username":"fixture", "isLive":"0", "isVerified":"1"])?.isVerified == true)
        precondition(FollowedChannel(snapshot: ["username":"fixture", "isLive":"1", "isVerified":true])?.isVerified == false)

        for style in PlayerControlAnimation.allCases {
            precondition(PlayerControlAnimation.effective(stored: style.rawValue, reduceMotion: false) == style)
            precondition(PlayerControlAnimation.effective(stored: style.rawValue, reduceMotion: true) == .fade)
        }
        precondition(PlayerControlAnimation.effective(stored: "unknown", reduceMotion: false) == .vertical)
        for style in PlayerControlAnimation.allCases {
            for region in [PlayerControlRegion.topLeading, .topTrailing, .bottomLeading, .bottomTrailing, .center, .shade] {
                let shown = PlayerControlMotion.frame(progress: 1, style: style, region: region, width: 400, height: 225)
                precondition(shown.x == 0 && shown.y == 0 && shown.opacity == 1)
                let hidden = PlayerControlMotion.frame(progress: 0, style: style, region: region, width: 400, height: 225)
                precondition(hidden.opacity == 0)
                if style == .fade { precondition(hidden.x == 0 && hidden.y == 0) }
            }
        }
        let travel = PlayerControlMotion.travel(canvasWidth: 400, canvasHeight: 225)
        precondition(travel.width == 188 && travel.height == 50)
        let narrow = PlayerControlMotion.travel(canvasWidth: 160, canvasHeight: 90)
        precondition(narrow.width == 160 && narrow.height == 50)
        for style in [PlayerControlAnimation.vertical, .horizontal] {
            // Exercise entry and reversed exit through the whole interval.
            // Center alpha must track normalized edge travel, with no separate phase.
            for step in 1..<100 {
                let progress = Double(step) / 100
                let center = PlayerControlMotion.frame(progress: progress, style: style, region: .center, width: 400, height: 225)
                precondition(center.x == 0 && center.y == 0 && center.opacity > 0 && center.opacity < 1)
                var pairedDistance: Double?
                for region in [PlayerControlRegion.topLeading, .topTrailing, .bottomLeading, .bottomTrailing] {
                    let edge = PlayerControlMotion.frame(progress: progress, style: style, region: region, width: travel.width, height: travel.height)
                    let absoluteDistance = abs(edge.x) + abs(edge.y)
                    if let pairedDistance { precondition(abs(absoluteDistance - pairedDistance) < 0.000001) }
                    else { pairedDistance = absoluteDistance }
                    let distance = style == .horizontal ? abs(edge.x) / travel.width : abs(edge.y) / travel.height
                    precondition(abs(distance + center.opacity - 1) < 0.000001, "Center and edges must finish together")
                }
            }
        }
        // No slow-start dead zone: ten percent of entry has already covered
        // over a quarter of the travel; Fade retains its existing curve.
        for style in [PlayerControlAnimation.vertical, .horizontal] {
            let early = PlayerControlMotion.frame(progress: 0.1, style: style, region: .center, width: 400, height: 225)
            precondition(early.opacity > 0.25 && early.opacity < 0.3)
        }
        let halfFade = PlayerControlMotion.frame(progress: 0.5, style: .fade, region: .topTrailing, width: 400, height: 225)
        precondition(abs(halfFade.opacity - 0.5) < 0.0001 && halfFade.x == 0 && halfFade.y == 0)
        var controls = PlayerControlsVisibility()
        controls.reveal(now: 100)
        controls.tick(now: 103.99, keepVisible: false); precondition(controls.visible)
        controls.tick(now: 104, keepVisible: false); precondition(!controls.visible)
        controls.toggle(now: 105); precondition(controls.visible)
        controls.tick(now: 109, keepVisible: true); precondition(controls.visible)
        controls.tick(now: 112.99, keepVisible: false); precondition(controls.visible)
        controls.tick(now: 113, keepVisible: false); precondition(!controls.visible)
        controls.reveal(now: 114); controls.toggle(now: 115); precondition(!controls.visible)
        precondition(StreamShareLink.url(username: "real_login123")?.absoluteString == "https://www.twitch.tv/real_login123")
        for name in ["", "../token", "user?token=x", "user@evil.invalid", "é", String(repeating: "a", count: 129)] {
            precondition(StreamShareLink.url(username: name) == nil)
        }
        // Tags stay structured, bounded, localized and absent for offline rows.
        let tagSnapshot: [String: Any] = ["username": "fixture", "isLive": "1", "tags": [" English ", "Anime", "English", "", "日本語"]]
        precondition(FollowedChannel(snapshot: tagSnapshot)?.tags == ["English", "Anime", "日本語"])
        precondition(FollowedChannel(snapshot: ["username": "fixture", "isLive": "0", "tags": ["stale"]])?.tags == [])
        precondition(FollowedChannel(snapshot: ["username": "fixture", "isLive": "1", "tags": 7])?.tags == [])
        precondition(FollowedChannel(snapshot: ["username": 7, "isLive": "1"]) == nil)
        precondition(StreamTagPacking.indices(widths: [110, 30, 30, 30], available: 102) == [1, 2, 3])
        precondition(StreamTagPacking.indices(widths: [60, 30, 30, 30], available: 102) == [1, 2, 3])
        precondition(StreamTagPacking.indices(widths: [60, 30, 30], available: 96) == [0, 1])
        precondition(StreamTagPacking.indices(widths: [90, 20], available: 20) == [1])
        precondition(StreamTagPacking.indices(widths: [.infinity, 20, .nan], available: 20) == [1])
        precondition(StreamTagPacking.indices(widths: [20], available: 19).isEmpty)
        // Exhaustive subset oracle independently checks maximum count and native
        // priority for every width in a small varied-width fixture.
        let tagWidths = [65.0, 22, 41, 18, 90, 35]
        for width in 0...260 {
            let selected = StreamTagPacking.indices(widths: tagWidths, available: Double(width))
            var best: [Int] = []
            for mask in 1..<(1 << tagWidths.count) {
                let indices = tagWidths.indices.filter { mask & (1 << $0) != 0 }
                let used = indices.map { tagWidths[$0] }.reduce(0, +) + Double(indices.count - 1) * 6
                if used <= Double(width), indices.count > best.count ||
                    (used <= Double(width) && indices.count == best.count && indices.lexicographicallyPrecedes(best)) { best = indices }
            }
            precondition(selected == best, "Tag packing lost width or native priority")
        }
        let account = StreamsideAccount(username: "fixture", displayName: "Fixture")
        let channels = [FollowedChannel(username: "channel", displayName: "Channel")]
        var state = NativeServiceState(phase: 4, account: account, channels: channels)
        precondition(state.session == .authenticated)
        state.enforceSessionBoundary()
        precondition(state.account == account && state.channels == channels)
        for phase in [0, 1, 2, 6, 7, 8, 9] {
            var next = NativeServiceState(phase: phase, account: account, channels: channels)
            next.enforceSessionBoundary()
            precondition(next.account == nil && next.channels.isEmpty, "Stale account data survived phase \(phase)")
        }
        for signOutState in [1, 2] {
            var next = NativeServiceState(phase: 4, account: account, channels: channels, signOutState: signOutState)
            next.enforceSessionBoundary()
            precondition(next.account == nil && next.channels.isEmpty)
        }
        let missing = NativeServiceState(phase: 4)
        precondition(missing.session == .failure)
        var loading = NativeServiceState(phase: 3, account: account, channels: channels)
        loading.enforceSessionBoundary()
        precondition(loading.account == account && loading.channels.isEmpty && loading.isBusy)
        precondition(NativeServiceState(phase: 1).session == .signedOut)
        for phase in [0, 1, 2, 6, 7, 8, 9] {
            let session = NativeServiceState(phase: phase, account: account).session
            precondition(!AuthenticationReturn.shouldReturn(session: session))
        }
        for phase in [3, 4, 5] {
            precondition(AuthenticationReturn.shouldReturn(session: NativeServiceState(phase: phase, account: account).session))
            precondition(!AuthenticationReturn.shouldReturn(session: NativeServiceState(phase: phase).session))
        }
        precondition(!AuthenticationReturn.shouldReturn(session: .signingOut))
        var feedFailure = NativeServiceState(phase: 10, account: account, channels: channels)
        feedFailure.enforceSessionBoundary()
        precondition(feedFailure.session == .authenticated && feedFailure.account == account && feedFailure.channels == channels)
        precondition(NativeServiceState(phase: 10).session == .failure)
        var refreshing = NativeServiceState(phase: 4, account: account, channels: channels, refreshing: true)
        refreshing.enforceSessionBoundary()
        precondition(refreshing.isBusy && refreshing.account == account && refreshing.channels == channels)
        refreshing.phase = 8 // Authoritative account invalidation always wins.
        refreshing.enforceSessionBoundary()
        precondition(refreshing.account == nil && refreshing.channels.isEmpty)
        for phone in [true, false] {
            for twoLines in [true, false] {
                precondition(FeedPreferences.titleLines(twoLines: twoLines, phone: phone, accessible: false) == (phone && twoLines ? 2 : 1))
                precondition(FeedPreferences.titleLines(twoLines: twoLines, phone: phone, accessible: true) == 3)
            }
        }
        let start = Date(timeIntervalSince1970: 100)
        precondition(StreamElapsed.seconds(startedAt: start, now: start.addingTimeInterval(1)) == 1)
        precondition(StreamElapsed.seconds(startedAt: start, now: start.addingTimeInterval(81)) == 81, "Resume must include elapsed background time")
        // Exercise the Foundation optional/value bridging used by the native
        // mapper, without assuming Optional, Date or URL memory layouts.
        struct CategoryFixture: Equatable { let title: String; let code: Int }
        let category = CategoryFixture(title: "Fixture", code: 1)
        let boxedCategory = Optional.some(category) as AnyObject
        let absentCategory = Optional<CategoryFixture>.none as AnyObject
        precondition(boxedCategory as? CategoryFixture == category)
        precondition(absentCategory is NSNull)
        precondition((Date(timeIntervalSince1970: 100) as AnyObject) is NSDate)
        precondition((Optional.some(URL(string: "https://static-cdn.jtvnw.net/image.jpg")!) as AnyObject) is NSURL)
        var gate = RefreshGate()
        precondition(gate.begin(now: 100))
        precondition(!gate.begin(now: 106), "Concurrent refresh bypassed the gate")
        gate.finish()
        precondition(!gate.begin(now: 104.999), "Five-second cooldown was bypassed")
        precondition(gate.begin(now: 105))
        gate.finish()
        var live = FollowedChannel(username: "live", displayName: "Live")
        live.isLive = true; live.viewerCount = 100
        var bigger = FollowedChannel(username: "big", displayName: "Big")
        bigger.isLive = true; bigger.viewerCount = 200
        let offline = FollowedChannel(username: "offline", displayName: "Offline")
        let stale = FollowedChannel(username: "LIVE", displayName: "Stale offline duplicate")
        let feed = FollowedFeed([offline, live, bigger, stale, live])
        precondition(feed.live.map { $0.username } == ["big", "live"])
        precondition(feed.offline.map { $0.username } == ["offline"])
        let mapped = FollowedChannel(snapshot: ["username":"fixture", "isLive":"1", "title":"Title", "category":"Category", "viewerCount":"1234", "startedAt":"100", "thumbnailRestricted":"1", "thumbnailURL":"https://static-cdn.jtvnw.net/image.jpg"])
        precondition(mapped?.viewerCount == 1234 && mapped?.thumbnailURL != nil && mapped?.thumbnailRestricted == true && mapped?.playbackAllowed == false)
        precondition(mapped?.startedAt == Date(timeIntervalSince1970: 100))
        precondition(FollowedChannel(snapshot:["username":"fixture"]) == nil, "Unknown status became offline")
        precondition(FollowedChannel(snapshot:["username":"fixture","isLive":"1","viewerCount":"-1"])?.viewerCount == nil)
        precondition(StreamElapsed.label(seconds: 3601) == "1:00:01")
        precondition(StreamElapsed.seconds(startedAt: Date(timeIntervalSince1970: 200), now: Date(timeIntervalSince1970: 100)) == 0)
        for text in ["https://static-cdn.jtvnw.net/preview.jpg", "https://static-cdn.jtvnw.net/avatar.png"] {
            precondition(ChannelImagePolicy.allowed(URL(string:text)!))
        }
        for text in ["http://static-cdn.jtvnw.net/image.jpg", "https://jtvnw.net.attacker.invalid/image.jpg", "https://user:pass@static-cdn.jtvnw.net/image.jpg", "https://static-cdn.jtvnw.net:8443/image.jpg", "file:///private/image.jpg"] {
            precondition(!ChannelImagePolicy.allowed(URL(string:text)!))
        }
        let cycles: [TimeInterval?] = [0.5, 1, 2.5, 3.75, 5, 10, nil]
        for index in 0...6 { precondition(LivePingCycle.seconds(index: index) == cycles[index]) }
        precondition(LivePingCycle.seconds(index: 2) == 2.5)
        precondition(LivePingCycle.seconds(index: -1) == 2.5 && LivePingCycle.seconds(index: 99) == 2.5)
        precondition(LivePingCycle.progress(at: 1.25, cycle: 2.5) == 0.5)
        precondition(LivePingCycle.progress(at: 2.5, cycle: 2.5) == 0)
        precondition(LivePingCycle.progress(at: -1.25, cycle: 2.5) == 0.5)
        precondition(LivePingCycle.progress(at: .infinity, cycle: 0) == 0)
        // A held endpoint must never produce repeated accepted selections.
        for endpoint in [0, 6] {
            var detent = CycleDetentSelection(index: endpoint)
            var ticks = 0
            for step in 0..<1000 {
                let offset = Double(step % 7 - 3) * 0.025
                if detent.move(to: Double(endpoint) + offset) { ticks += 1 }
                precondition(!detent.step(increasing: endpoint == 6))
            }
            precondition(ticks == 0 && detent.index == endpoint, "Endpoint jitter emitted a tick")
        }
        var detent = CycleDetentSelection(index: 2)
        precondition(!detent.move(to: 2.5))
        precondition(detent.move(to: 2.63) && detent.index == 3)
        for position in [2.48, 2.52, 2.4, 2.6] { precondition(!detent.move(to: position)) }
        precondition(detent.move(to: 2.37) && detent.index == 2)
        precondition(detent.move(to: 100) && detent.index == 6)
        precondition(!detent.move(to: 100) && !detent.move(to: .infinity) && !detent.move(to: .nan))
        precondition(detent.move(to: -100) && detent.index == 0)
        for value in 1...6 { precondition(detent.step(increasing: true) && detent.index == value) }
        precondition(!detent.step(increasing: true))
        for value in (0...5).reversed() { precondition(detent.step(increasing: false) && detent.index == value) }
        precondition(!detent.step(increasing: false))
        print("PASS: session boundaries, feed grouping/fields, five-second refresh gate, elapsed time and image URL policy")
    }
}
