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
    static let livePingIndexKey = "dev.streamside.feed.livePingIndex"
    static let twoLineTitlesKey = "dev.streamside.feed.twoLineTitles"
    static func titleLines(twoLines: Bool, phone: Bool, accessible: Bool) -> Int {
        accessible ? 3 : (phone && twoLines ? 2 : 1)
    }
}

enum LivePingCycle {
    static let labels = ["0.5s", "1s", "2.5s", "3.75s", "5s", "10s", "Off"]
    static func normalized(_ index: Int) -> Int { (0...6).contains(index) ? index : 2 }
    static func seconds(index: Int) -> TimeInterval? {
        let choices: [TimeInterval?] = [0.5, 1, 2.5, 3.75, 5, 10, nil]
        return choices[normalized(index)]
    }
    static func label(index: Int) -> String { labels[normalized(index)] }
    static func progress(at time: TimeInterval, cycle: TimeInterval) -> Double {
        guard time.isFinite, cycle.isFinite, cycle > 0 else { return 0 }
        return ((time.truncatingRemainder(dividingBy: cycle) + cycle).truncatingRemainder(dividingBy: cycle)) / cycle
    }
}

// Selection changes, rather than raw drag callbacks, are the haptic boundary.
// The extra 0.12-stop dead band prevents repeated toggling at a midpoint.
struct CycleDetentSelection {
    private(set) var index: Int
    init(index: Int) { self.index = LivePingCycle.normalized(index) }
    mutating func move(to position: Double) -> Bool {
        guard position.isFinite else { return false }
        let bounded = min(6, max(0, position))
        let candidate = Int(bounded.rounded())
        guard candidate != index, abs(bounded - Double(index)) >= 0.62 else { return false }
        index = candidate
        return true
    }
    mutating func step(increasing: Bool) -> Bool {
        let next = increasing ? min(6, index + 1) : max(0, index - 1)
        guard next != index else { return false }
        index = next
        return true
    }
}

// Per-player presentation settings. Accessibility preferences take precedence.
enum PlayerPreferences {
    static let glassButtonsKey = "dev.streamside.player.glassButtons"
}

// Monotonic time prevents wall-clock adjustments from extending controls.
struct PlayerControlsVisibility {
    static let timeout: TimeInterval = 4
    private(set) var visible = true
    private var hideAt: TimeInterval = .infinity
    mutating func reveal(now: TimeInterval) { visible = true; hideAt = now + Self.timeout }
    mutating func toggle(now: TimeInterval) {
        if visible { visible = false } else { reveal(now: now) }
    }
    mutating func tick(now: TimeInterval, keepVisible: Bool) {
        if keepVisible { reveal(now: now) }
        else if now >= hideAt { visible = false }
    }
}

enum StreamShareLink {
    static func url(username: String) -> URL? {
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        guard !username.isEmpty, username.count <= 128,
              username.rangeOfCharacter(from: allowed.inverted) == nil else { return nil }
        return URL(string: "https://www.twitch.tv/" + username)
    }
}
