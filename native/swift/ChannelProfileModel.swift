import Combine
import Foundation

enum ProfileOperation: Int { case profile, relationship, unfollow, follow, notifications }
@MainActor protocol ChannelProfileBackend {
    func request(channelID: String, operation: ProfileOperation, setting: String) async throws -> [String: Any]
}
struct ChannelProfileData {
    struct Link: Identifiable { let id: String; let title: String; let url: URL }
    struct Panel: Identifiable { let id: Int; let title: String; let text: String; let image: URL?; let link: URL?; let supported: Bool }
    let name: String
    let bio: String
    let avatar: URL?
    let banner: URL?
    let followers: Int?
    let links: [Link]
    let panels: [Panel]
    static func url(_ value: Any?) -> URL? {
        guard let text = value as? String, text.count <= 2048, let url = URL(string: text),
              ["https", "http"].contains(url.scheme?.lowercased() ?? ""), url.host != nil,
              url.user == nil, url.password == nil else { return nil }
        return url
    }
    init?(result: [String: Any]) {
        guard let user = result["user"] as? [String: Any], let name = user["displayName"] as? String else { return nil }
        self.name = String(name.prefix(256)); bio = String((user["description"] as? String ?? "").prefix(16000))
        avatar = Self.url(user["profileImageURL"]); banner = Self.url(user["bannerImageURL"])
        followers = (user["followers"] as? [String: Any])?["totalCount"] as? Int
        let channel = user["channel"] as? [String: Any]
        links = (channel?["socialMedias"] as? [[String: Any]] ?? []).prefix(32).compactMap { row in
            guard let url = Self.url(row["url"]), let title = row["title"] as? String else { return nil }
            return Link(id: row["id"] as? String ?? url.absoluteString, title: String(title.prefix(256)), url: url)
        }
        panels = (user["panels"] as? [Any] ?? []).prefix(64).enumerated().compactMap { index, value in
            guard let row = value as? [String: Any] else { return nil }
            return Panel(id: index, title: String((row["title"] as? String ?? "").prefix(512)),
                text: String((row["description"] as? String ?? "").prefix(16000)), image: Self.url(row["imageURL"]),
                link: Self.url(row["linkURL"]), supported: row["__typename"] as? String == "DefaultPanel")
        }
    }
}
struct ChannelRelationship: Equatable {
    let followed: Bool
    let canFollow: Bool
    let setting: String?
    init?(result: [String: Any]) {
        guard let user = result["user"] as? [String: Any], let connection = user["connection"] as? [String: Any] else { return nil }
        let follower = connection["follower"] as? [String: Any]
        followed = follower != nil; canFollow = connection["canFollow"] as? Bool ?? false
        let settings = follower?["notificationSettings"] as? [String: Any]
        let raw = settings?["followsSettingState"] as? String
        setting = NotificationChoice.allCases.contains { $0.rawValue == raw } ? raw : nil
    }
}
enum NotificationChoice: String, CaseIterable, Identifiable {
    case personalized = "PERSONALIZED", always = "ALWAYS", liveOnly = "LIVE_UP_ONLY", off = "NEVER"
    var id: String { rawValue }
    var title: String { switch self { case .personalized: return "Personalized"; case .always: return "Always"; case .liveOnly: return "Go Live Only"; case .off: return "Off" } }
    var icon: String { switch self { case .personalized: return "bell.badge.fill"; case .always: return "bell.fill"; case .liveOnly: return "bell"; case .off: return "bell.slash" } }
}
@MainActor final class ChannelProfileModel: ObservableObject {
    @Published var tab = 0
    @Published private(set) var data: ChannelProfileData?
    @Published private(set) var relationship: ChannelRelationship?
    @Published private(set) var busy = false
    @Published private(set) var error: String?
    let channel: FollowedChannel
    private let backend: ChannelProfileBackend
    private let valid: () -> Bool
    private let changed: () -> Void
    init(channel: FollowedChannel, backend: ChannelProfileBackend, valid: @escaping () -> Bool, changed: @escaping () -> Void = {}) {
        self.channel = channel; self.backend = backend; self.valid = valid; self.changed = changed
    }
    private func request(_ operation: ProfileOperation, setting: String = "") async throws -> [String: Any] {
        guard valid(), !Task.isCancelled else { throw CancellationError() }
        let result = try await backend.request(channelID: channel.channelID, operation: operation, setting: setting)
        guard valid(), !Task.isCancelled else { throw CancellationError() }; return result
    }
    func load() async {
        guard !busy, valid(), channel.localTest == nil else { return }; busy = true; error = nil
        defer { busy = false }
        do {
            guard let next = ChannelProfileData(result: try await request(.profile)) else { throw CocoaError(.coderReadCorrupt) }
            data = next
            guard let state = ChannelRelationship(result: try await request(.relationship)) else { throw CocoaError(.coderReadCorrupt) }
            relationship = state
        } catch is CancellationError { } catch { self.error = "The channel profile could not be loaded. Try again." }
    }
    func change(_ operation: ProfileOperation, setting: String = "") async -> Bool {
        guard !busy, valid(), let relationship, channel.localTest == nil,
              (operation == .unfollow && relationship.followed) || (operation == .follow && !relationship.followed && relationship.canFollow) ||
              (operation == .notifications && relationship.followed && NotificationChoice.allCases.contains(where: { $0.rawValue == setting })) else { return false }
        busy = true; error = nil; defer { busy = false }
        do {
            let result = try await request(operation, setting: setting)
            let key = operation == .unfollow ? "unfollowUser" : operation == .follow ? "followUser" : "setLiveNotificationsEnrollment"
            guard let payload = result[key] as? [String: Any], payload["error"] == nil || payload["error"] is NSNull else { throw CocoaError(.coderReadCorrupt) }
            guard let next = ChannelRelationship(result: try await request(.relationship)),
                  operation == .notifications ? next.setting == setting : next.followed == (operation == .follow) else { throw CocoaError(.coderReadCorrupt) }
            self.relationship = next; changed(); return true
        } catch is CancellationError { return false } catch { error = "The change could not be confirmed. Refresh before trying again."; return false }
    }
}
