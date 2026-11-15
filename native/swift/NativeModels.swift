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
    var tags: [String] = []
    var viewerCount: Int?
    var startedAt: Date?
    var avatarURL: URL?
    var thumbnailURL: URL?
    var thumbnailRestricted = false
    var id: String { username }

    init(username: String, displayName: String) {
        self.username = username; self.displayName = displayName
    }
    init?(snapshot: [String: Any]) {
        guard let username = snapshot["username"] as? String, !username.isEmpty,
              let live = snapshot["isLive"] as? String, live == "0" || live == "1" else { return nil }
        self.init(username: username, displayName: snapshot["displayName"] as? String ?? username)
        isLive = live == "1"
        title = snapshot["title"] as? String ?? ""
        category = snapshot["category"] as? String ?? ""
        if isLive { tags = StreamTagPacking.names(snapshot["tags"] as? [String] ?? []) }
        if let text = snapshot["viewerCount"] as? String, let count = Int(text), count >= 0 { viewerCount = count }
        if let text = snapshot["startedAt"] as? String, let epoch = Double(text), epoch.isFinite, epoch > 0 {
            startedAt = Date(timeIntervalSince1970: epoch)
        }
        avatarURL = (snapshot["avatarURL"] as? String).flatMap(URL.init(string:))
        thumbnailURL = (snapshot["thumbnailURL"] as? String).flatMap(URL.init(string:))
        thumbnailRestricted = snapshot["thumbnailRestricted"] as? String == "1"
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
    static let animationKey = "dev.streamside.player.controlAnimation"
}

enum PlayerControlAnimation: String, CaseIterable, Identifiable {
    case vertical, horizontal, fade
    var id: String { rawValue }
    var title: String {
        switch self {
        case .vertical: return "Top / bottom"
        case .horizontal: return "Left / right"
        case .fade: return "Fade"
        }
    }
    static func effective(stored: String, reduceMotion: Bool) -> Self {
        reduceMotion ? .fade : (Self(rawValue: stored) ?? .vertical)
    }
}

// One reversible presentation timeline: the stationary center fade and edge
// travel start and finish together, independently of the material setting.
enum PlayerControlRegion: Hashable { case topLeading, topTrailing, bottomLeading, bottomTrailing, center, shade }
struct PlayerControlFrame {
    let x: Double
    let y: Double
    let opacity: Double
}
enum PlayerControlMotion {
    static let canvasInset = 6.0
    static let controlsHeight = 44.0
    static let actionsWidth = 182.0
    // Equal displacement gives every edge the same points-per-second curve.
    // Use logical control layout, never material-dependent rendered bounds.
    static func travel(canvasWidth: Double, canvasHeight: Double) -> (width: Double, height: Double) {
        (min(canvasWidth, actionsWidth + canvasInset), min(canvasHeight, controlsHeight + canvasInset))
    }
    static let flyDuration = 0.70
    static let fadeDuration = 0.26
    static func duration(style: PlayerControlAnimation) -> Double { style == .fade ? fadeDuration : flyDuration }
    private static func smooth(_ value: Double) -> Double {
        let t = min(1, max(0, value))
        return t * t * t * (t * (6 * t - 15) + 10)
    }
    static func frame(progress: Double, style: PlayerControlAnimation, region: PlayerControlRegion,
                      width: Double, height: Double) -> PlayerControlFrame {
        let p = min(1, max(0, progress))
        if style == .fade {
            return PlayerControlFrame(x: 0, y: 0, opacity: smooth(p))
        }
        // Cubic ease-out starts moving immediately and settles with zero
        // velocity. Reversing this same curve preserves position on interruption.
        let remaining = (1 - p) * (1 - p) * (1 - p)
        if region == .center || region == .shade {
            return PlayerControlFrame(x: 0, y: 0, opacity: 1 - remaining)
        }
        let leading = region == .topLeading || region == .bottomLeading
        let top = region == .topLeading || region == .topTrailing
        return PlayerControlFrame(x: style == .horizontal ? (leading ? -width : width) * remaining : 0,
                                  y: style == .vertical ? (top ? -height : height) * remaining : 0,
                                  opacity: p == 0 ? 0 : 1)
    }
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


// Choose the most complete pills that fit. Among equally full selections,
// prefer earlier native tags and keep their presentation order unchanged.
enum StreamTagPacking {
    static func names(_ input: [String]) -> [String] {
        var seen = Set<String>()
        return input.prefix(100).compactMap { raw in
            let name = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !name.isEmpty, name.utf16.count <= 256,
                  name.rangeOfCharacter(from: .controlCharacters) == nil,
                  seen.insert(name.lowercased()).inserted else { return nil }
            return name
        }.prefix(32).map { $0 }
    }
    static func indices(widths: [Double], available: Double, spacing: Double = 6) -> [Int] {
        guard available.isFinite, available > 0, spacing.isFinite, spacing >= 0 else { return [] }
        let candidates = widths.prefix(32).enumerated().filter { $0.element.isFinite && $0.element > 0 }
        var remaining = available + spacing
        var count = 0, sum = 0.0
        for width in candidates.map({ $0.element + spacing }).sorted() {
            if sum + width > remaining { break }
            sum += width; count += 1
        }
        var selected: [Int] = []
        for (position, candidate) in candidates.enumerated() where count > 0 {
            let cost = candidate.element + spacing
            let suffix = candidates.dropFirst(position + 1).map { $0.element + spacing }.sorted()
            guard suffix.count >= count - 1,
                  cost + suffix.prefix(count - 1).reduce(0, +) <= remaining else { continue }
            selected.append(candidate.offset); remaining -= cost; count -= 1
        }
        return selected
    }
}
