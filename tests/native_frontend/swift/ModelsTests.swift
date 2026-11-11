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
        print("PASS: authenticated, signed-out, account-change, failure, logout and loading presentation boundaries")
    }
}
