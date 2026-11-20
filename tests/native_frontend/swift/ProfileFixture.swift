import SwiftUI
import UIKit

@MainActor private final class ProfileFixtureBackend: ChannelProfileBackend {
    let relationshipUnavailable = ProcessInfo.processInfo.arguments.contains("--profile-relationship-failure")
    var followed = true
    var setting = "PERSONALIZED"
    func request(channelID: String, operation: ProfileOperation, setting: String) async throws -> [String: Any] {
        switch operation {
        case .profile:
            let user: [String: Any] = ["displayName": "Profile fixture", "description": "Fixture biography", "followers": ["totalCount": 123],
            "panels": [["__typename": "DefaultPanel", "title": "Fixture panel", "description": "About panel body"]]]
            return ["user": user]
        case .relationship:
            if relationshipUnavailable { throw CocoaError(.coderReadCorrupt) }
            let follower: Any = followed ? ["notificationSettings": ["followsSettingState": self.setting]] : NSNull()
            let connection: [String: Any] = ["canFollow": true, "follower": follower]
            return ["user": ["connection": connection]]
        case .unfollow: followed = false;return ["unfollowUser": ["follow": NSNull()]]
        case .follow: followed = true;return ["followUser": ["error": NSNull()]]
        case .notifications: self.setting = setting;return ["setLiveNotificationsEnrollment": ["error": NSNull()]]
        }
    }
}
struct ProfileFixture: View {
    @StateObject private var model: ChannelProfileModel
    private let images = ChannelImageCache()
    private let clock = StreamClock()
    @State private var closed = false
    init() {
        var channel = FollowedChannel(username: "fixture", displayName: "Profile fixture")
        channel.channelID = "123"
        channel.isLive = true
        channel.category = "A long live category name that must wrap inside the profile viewport"
        channel.viewerCount = 75_231
        _model = StateObject(wrappedValue: ChannelProfileModel(channel: channel, backend: ProfileFixtureBackend(), valid: { true }))
    }
    var body: some View {
        if closed { Text("Profile closed").accessibilityIdentifier("profile.closed") }
        else {
            ChannelProfileView(model: model, images: images, clock: clock, close: { closed = true }) {
                Color.indigo.aspectRatio(16.0 / 9.0, contentMode: .fit)
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel("Fixture live preview")
                    .accessibilityIdentifier("profile.fixture-preview")
            }
        }
    }
}
