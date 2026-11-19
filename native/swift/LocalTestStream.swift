import Foundation
import Combine

enum DevelopmentTools {
    static var enabled: Bool {
#if SSN_DEVELOPMENT
        true
#else
        false
#endif
    }
}

// A typed local origin, never decoded from a Twitch snapshot or a channel name.
struct LocalTestStream: Codable, Equatable {
    enum Status: String, Codable, CaseIterable, Hashable { case ready, loading, buffering
        var phase: Int { self == .ready ? 3 : self == .loading ? 2 : 4 }
    }
    var enabled = false
    var username = "local_test"
    var name = "Test channel"
    var title = "A local stream for testing titles, content warnings and preview layout"
    var category = "Just Chatting"
    var tags = "English, Local test"
    var marked = true
    var labels = "Sexual Themes"
    var live = true
    var verified = false
    var viewers = 123
    var startedAt = Date().addingTimeInterval(-3600)
    var status = Status.buffering
    var contentLabels: [String] { names(labels) }
    private func names(_ text: String) -> [String] {
        Array(StreamTagPacking.names(text.components(separatedBy: CharacterSet(charactersIn: ",\n"))).prefix(10))
    }
    var normalized: Self {
        var value = self
        value.username = String(username.prefix(80)); value.name = String(name.prefix(80))
        value.title = String(title.prefix(2000)); value.category = String(category.prefix(160))
        value.tags = String(tags.prefix(2000)); value.labels = String(labels.prefix(2000))
        value.viewers = min(999999, max(0, viewers))
        if value.marked && value.contentLabels.isEmpty { value.labels = "Test content label" }
        if !value.startedAt.timeIntervalSince1970.isFinite { value.startedAt = Date() }
        return value
    }
    var channel: FollowedChannel {
        let value = normalized
        var channel = FollowedChannel(username: value.username, displayName: "Local test · " + value.name)
        channel.isLive = value.live; channel.isVerified = value.verified
        channel.title = value.title; channel.category = value.category; channel.tags = names(value.tags)
        channel.viewerCount = value.viewers; channel.startedAt = value.live ? value.startedAt : nil
        channel.thumbnailRestricted = value.marked
        channel.localTest = value
        // Intentionally no URL, native channel ID, or external media source.
        return channel
    }
}

@MainActor final class LocalTestStreamStore: ObservableObject {
    static let key = "dev.streamside.diagnostics.localTestStream"
    @Published private(set) var value = LocalTestStream()
    private let defaults: UserDefaults
    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        guard DevelopmentTools.enabled, let data = defaults.data(forKey: Self.key), data.count <= 65536,
              let saved = try? JSONDecoder().decode(LocalTestStream.self, from: data) else { return }
        value = saved.normalized
    }
    var channel: FollowedChannel? { DevelopmentTools.enabled && value.enabled ? value.channel : nil }
    func save(_ draft: LocalTestStream) {
        guard DevelopmentTools.enabled else { return }
        value = draft.normalized
        if let data = try? JSONEncoder().encode(value) { defaults.set(data, forKey: Self.key) }
    }
    func remove() { var draft = value; draft.enabled = false; save(draft) }
}
