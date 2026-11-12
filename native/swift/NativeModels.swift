import Foundation

struct StreamsideAccount: Equatable {
    let username: String
    let displayName: String
}

struct FollowedChannel: Identifiable, Equatable {
    let username: String
    let displayName: String
    var isLive = false
    var title = ""
    var category = ""
    var viewerCount: Int?
    var startedAt: Date?
    var avatarURL: URL?
    var thumbnailURL: URL?
    var thumbnailRestricted = false
    var id: String { username }

    init(username: String, displayName: String) {
        self.username = username; self.displayName = displayName
    }
    init?(snapshot: [String: String]) {
        guard let username = snapshot["username"], !username.isEmpty,
              snapshot["isLive"] == "0" || snapshot["isLive"] == "1" else { return nil }
        self.init(username: username, displayName: snapshot["displayName"] ?? username)
        isLive = snapshot["isLive"] == "1"
        title = snapshot["title"] ?? ""
        category = snapshot["category"] ?? ""
        if let text = snapshot["viewerCount"], let count = Int(text), count >= 0 { viewerCount = count }
        if let text = snapshot["startedAt"], let epoch = Double(text), epoch.isFinite, epoch > 0 {
            startedAt = Date(timeIntervalSince1970: epoch)
        }
        avatarURL = snapshot["avatarURL"].flatMap(URL.init(string:))
        thumbnailURL = snapshot["thumbnailURL"].flatMap(URL.init(string:))
        thumbnailRestricted = snapshot["thumbnailRestricted"] == "1"
        if thumbnailRestricted { thumbnailURL = nil }
    }
}

enum SessionPresentation: Equatable {
    case restoring, signedOut, checkingAccount, authenticated, signingOut
    case failure, unavailable

    static func resolve(phase: Int, hasAccount: Bool, signOutState: Int) -> Self {
        if signOutState == 1 { return .signingOut }
        if signOutState == 2 { return .failure }
        switch phase {
        case 1: return .signedOut
        case 2: return .checkingAccount
        case 3, 4, 5, 10: return hasAccount ? .authenticated : .failure
        case 6: return .failure
        case 7, 9: return .unavailable
        default: return .restoring
        }
    }
}

struct NativeServiceState {
    var phase = 0
    var account: StreamsideAccount?
    var channels: [FollowedChannel] = []
    var signOutState = 0
    var canSignOut = false
    var refreshing = false
    var session: SessionPresentation {
        SessionPresentation.resolve(phase: phase, hasAccount: account != nil, signOutState: signOutState)
    }
    var isBusy: Bool {
        refreshing || session == .checkingAccount || session == .restoring || session == .signingOut || phase == 3
    }
    // State changes immediately remove presentation data; a saved diagnostic
    // file from another process can never supply account/channel UI content.
    mutating func enforceSessionBoundary() {
        if session != .authenticated { account = nil; channels = [] }
        if phase != 4 && phase != 5 && phase != 10 { channels = [] }
    }
}

// Native currentUser verification produces .authenticated before follows finish.
// A notification, saved token presence, or stale account alone is insufficient.
enum AuthenticationReturn {
    static func shouldReturn(session: SessionPresentation) -> Bool {
        session == .authenticated
    }
}

struct FollowedFeed {
    let live: [FollowedChannel]
    let offline: [FollowedChannel]
    init(_ channels: [FollowedChannel]) {
        // Prefer a live record if Twitch returns the same channel in both sections.
        var seen = Set<String>()
        live = channels.filter { $0.isLive }.sorted {
            let lhs = $0.viewerCount ?? -1, rhs = $1.viewerCount ?? -1
            return lhs != rhs ? lhs > rhs : $0.username.localizedStandardCompare($1.username) == .orderedAscending
        }.filter { seen.insert($0.id.lowercased()).inserted }
        offline = channels.filter { !$0.isLive }.sorted {
            $0.displayName.localizedStandardCompare($1.displayName) == .orderedAscending
        }.filter { seen.insert($0.id.lowercased()).inserted }
    }
}

struct RefreshGate {
    private(set) var lastAccepted: TimeInterval?
    private(set) var inFlight = false
    let interval: TimeInterval = 5
    mutating func begin(now: TimeInterval) -> Bool {
        guard !inFlight, remaining(now: now) == 0 else { return false }
        inFlight = true; lastAccepted = now; return true
    }
    func remaining(now: TimeInterval) -> TimeInterval {
        guard let lastAccepted else { return 0 }
        return max(0, interval - (now - lastAccepted))
    }
    mutating func finish() { inFlight = false }
}

struct StreamElapsed {
    static func seconds(startedAt: Date, now: Date) -> Int {
        let duration = now.timeIntervalSince(startedAt)
        guard duration.isFinite, duration > 0 else { return 0 }
        return Int(min(duration, 31_536_000))
    }
    static func label(seconds: Int) -> String {
        let value = max(0, seconds)
        return String(format: "%d:%02d:%02d", value / 3600, value / 60 % 60, value % 60)
    }
}


enum ChannelImagePolicy {
    static func allowed(_ url: URL) -> Bool {
        guard url.scheme == "https", url.user == nil, url.password == nil,
              url.port == nil || url.port == 443, let host = url.host?.lowercased() else { return false }
        return host == "jtvnw.net" || host.hasSuffix(".jtvnw.net")
    }
}

enum FeedPreferences {
    static let twoLineTitlesKey = "dev.streamside.feed.twoLineTitles"
    static func titleLines(twoLines: Bool, phone: Bool, accessible: Bool) -> Int {
        accessible ? 3 : (phone && twoLines ? 2 : 1)
    }
}
