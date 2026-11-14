import Foundation

// Synthetic presentation fixtures. No donor, network or live account is used.
@main struct ModelsTests {
    static func main() {
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
        for style in [PlayerControlAnimation.vertical, .horizontal] {
            let earlyCenter = PlayerControlMotion.frame(progress: 0.4, style: style, region: .center, width: 400, height: 225)
            let lateCenter = PlayerControlMotion.frame(progress: 0.85, style: style, region: .center, width: 400, height: 225)
            let lateEdge = PlayerControlMotion.frame(progress: 0.85, style: style, region: .topTrailing, width: 400, height: 225)
            precondition(earlyCenter.opacity == 0 && lateCenter.opacity > 0 && lateCenter.opacity < 1)
            precondition(lateCenter.x == 0 && lateCenter.y == 0 && lateEdge.x == 0 && lateEdge.y == 0)
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
        precondition(mapped?.viewerCount == 1234 && mapped?.thumbnailURL == nil)
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
