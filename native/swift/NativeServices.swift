import Combine
import Foundation

@MainActor
protocol AccountService: ObservableObject {
    var state: NativeServiceState { get }
    func refresh()
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
        next.phase = (snapshot["phase"] as? NSNumber)?.intValue ?? 9
        next.signOutState = (snapshot["signOutState"] as? NSNumber)?.intValue ?? 0
        next.canSignOut = (snapshot["canSignOut"] as? NSNumber)?.boolValue ?? false
        if let account = snapshot["account"] as? [String: String],
           let name = account["username"], !name.isEmpty {
            next.account = StreamsideAccount(username: name, displayName: account["displayName"] ?? name)
        }
        next.channels = (snapshot["channels"] as? [[String: String]] ?? []).compactMap {
            guard let name = $0["username"], !name.isEmpty else { return nil }
            return FollowedChannel(username: name, displayName: $0["displayName"] ?? name)
        }
        next.enforceSessionBoundary()
        state = next
        diagnosticSummary = snapshot["summary"] as? String ?? "Diagnostics unavailable"
        runtimeCounts = (snapshot["runtimeCounts"] as? [[String: Any]] ?? []).compactMap {
            guard let name = $0["name"] as? String, let count = $0["count"] as? NSNumber else { return nil }
            return RuntimeObservation(name: name, count: count.uint64Value,
                                      guarded: ($0["guarded"] as? NSNumber)?.boolValue ?? true)
        }
        if next.signOutState == 2 { actionError = "Sign-out could not be confirmed. Check your account and try again." }
    }

    func refresh() { actionError = nil; bridge.refresh(); reloadSnapshot() }
    func signOut() {
        actionError = nil
        if !bridge.beginSignOut() { actionError = "Sign-out is unavailable. Check diagnostics before trying again." }
        reloadSnapshot()
    }
    func exportReports() -> [URL] { bridge.exportReports() }
}
