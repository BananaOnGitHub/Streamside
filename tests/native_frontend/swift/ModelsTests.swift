import Foundation

// Synthetic presentation fixtures. No donor, network or live account is used.
@main struct ModelsTests {
    static func main() {
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
        precondition(feedFailure.session == .authenticated && feedFailure.account == account && feedFailure.channels.isEmpty)
        precondition(NativeServiceState(phase: 10).session == .failure)
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
        print("PASS: session boundaries, feed grouping/fields, five-second refresh gate, elapsed time and image URL policy")
    }
}
