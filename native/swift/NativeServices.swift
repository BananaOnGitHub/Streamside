import Combine
import Foundation

@MainActor
protocol AccountService: ObservableObject {
    var state: NativeServiceState { get }
    func refresh() async
    func signOut()
}

struct RuntimeObservation: Identifiable {
    let name: String
    let count: UInt64
    let guarded: Bool
    var id: String { name }
}

@MainActor
final class NativeServices: ObservableObject, AccountService {
    @Published private(set) var state = NativeServiceState()
    @Published private(set) var diagnosticSummary = "Waiting for diagnostics"
    @Published private(set) var runtimeCounts: [RuntimeObservation] = []
    @Published private(set) var actionError: String?
    @Published private(set) var rootOwner = 0
    @Published var canSignIn = false
    @Published private(set) var isRefreshing = false
    @Published private(set) var refreshMessage: String?
    @Published private(set) var imageGeneration: UInt64 = 0
    private var refreshGate = RefreshGate()
    let images = ChannelImageCache()
    let clock = StreamClock()
    let titleHaptics = TitleHaptics()
    private let bridge = SSNNativeBridge.shared()
    private var changes: AnyCancellable?

    init() {
        changes = NotificationCenter.default.publisher(for: .SSNNativeServiceDidChange)
            .receive(on: RunLoop.main)
            .sink { [weak self] _ in self?.reloadSnapshot() }
        reloadSnapshot()
    }

    func reloadSnapshot() {
        let snapshot = bridge.snapshot()
        var next = NativeServiceState()
        next.refreshing = (snapshot["refreshing"] as? NSNumber)?.boolValue ?? false
        next.phase = (snapshot["phase"] as? NSNumber)?.intValue ?? 9
        next.signOutState = (snapshot["signOutState"] as? NSNumber)?.intValue ?? 0
        next.canSignOut = (snapshot["canSignOut"] as? NSNumber)?.boolValue ?? false
        if let account = snapshot["account"] as? [String: String],
           let name = account["username"], !name.isEmpty {
            next.account = StreamsideAccount(username: name, displayName: account["displayName"] ?? name)
        }
        next.channels = (snapshot["channels"] as? [[String: String]] ?? []).compactMap {
            FollowedChannel(snapshot: $0)
        }
        next.enforceSessionBoundary()
        state = next
        rootOwner = (snapshot["rootOwner"] as? NSNumber)?.intValue ?? 0
        diagnosticSummary = snapshot["summary"] as? String ?? "Diagnostics unavailable"
        runtimeCounts = (snapshot["runtimeCounts"] as? [[String: Any]] ?? []).compactMap {
            guard let name = $0["name"] as? String, let count = $0["count"] as? NSNumber else { return nil }
            return RuntimeObservation(name: name, count: count.uint64Value,
                                      guarded: ($0["guarded"] as? NSNumber)?.boolValue ?? true)
        }
        if next.signOutState == 2 { actionError = "Sign-out could not be confirmed. Check your account and try again." }
    }

    func actionUnavailable() { actionError = "Native navigation ownership is unavailable. Export diagnostics." }
    func signIn() {
        actionError = nil
        if !SSNSwiftUIHost.beginSignIn() {
            actionError = "Twitch’s native sign-in screen is not ready. Refresh and export diagnostics if this persists."
        }
    }
    func refresh() async {
        actionError = nil
        guard !state.isBusy, refreshGate.begin(now: ProcessInfo.processInfo.systemUptime) else {
            let remaining = Int(ceil(refreshGate.remaining(now: ProcessInfo.processInfo.systemUptime)))
            refreshMessage = remaining > 0 ? "Allow five seconds between refreshes." : "Refresh is already in progress."
            return
        }
        isRefreshing = true; refreshMessage = nil; imageGeneration &+= 1
        defer { isRefreshing = false; refreshGate.finish() }
        bridge.refresh(); reloadSnapshot()
        // Donor requests own cancellation and the 30s service timeout. This only
        // covers both sequential native stages while keeping the indicator alive.
        for _ in 0..<640 {
            if !state.isBusy { break }
            do { try await Task.sleep(nanoseconds: 100_000_000) } catch { break }
        }
    }
    func signOut() {
        actionError = nil
        if !bridge.beginSignOut() { actionError = "Sign-out is unavailable. Check diagnostics before trying again." }
        reloadSnapshot()
    }
    func exportReports() -> [URL] { bridge.exportReports() }
}
