import Foundation

@MainActor private final class FixtureBackend: ChannelProfileBackend {
    var followed = true, stale = false, failing = false, malformed = false
    var setting = "PERSONALIZED"
    var calls: [ProfileOperation] = []
    var during: (() -> Void)?
    func request(channelID: String, operation: ProfileOperation, setting: String) async throws -> [String: Any] {
        precondition(channelID == "123"); calls.append(operation); during?()
        if failing { throw CocoaError(.coderReadCorrupt) }
        switch operation {
        case .profile:
            if malformed { return [:] }
            let user: [String: Any] = ["displayName": "Fixture", "description": "Bio", "bannerImageURL": "https://static-cdn.jtvnw.net/banner.jpg",
            "followers": ["totalCount": 1234], "channel": ["socialMedias": [["id": "1", "title": "Social", "url": "https://example.com"]]],
            "panels": [["__typename": "DefaultPanel", "title": "About fixture", "description": "Panel text"], ["__typename": "ExtensionPanel"]]]
            return ["user": user]
        case .relationship:
            let follower: Any = followed ? ["notificationSettings": ["followsSettingState": self.setting]] : NSNull()
            let connection: [String: Any] = ["canFollow": true, "follower": follower]
            return ["user": ["connection": connection]]
        case .unfollow: if !stale { followed = false }; return ["unfollowUser": ["follow": NSNull()]]
        case .follow: if !stale { followed = true }; return ["followUser": ["error": NSNull()]]
        case .notifications: if !stale { self.setting = setting }; return ["setLiveNotificationsEnrollment": ["error": NSNull()]]
        }
    }
}
@main struct ProfileTests {
    @MainActor static func main() async {
        var channel = FollowedChannel(username: "fixture", displayName: "Fixture"); channel.channelID = "123"
        let backend = FixtureBackend();var valid = true, changes = 0
        var rejections: [ProfileOperation] = []
        let model = ChannelProfileModel(channel: channel, backend: backend, valid: { valid }, changed: { changes += 1 }, rejected: { rejections.append($0) })
        await model.load()
        precondition(model.data?.followers == 1234 && model.data?.bio == "Bio" && model.data?.links.count == 1)
        precondition(model.data?.panels.count == 2 && model.data?.panels[0].supported == true && model.data?.panels[1].supported == false)
        precondition(model.relationship?.followed == true && model.relationship?.setting == "PERSONALIZED")
        precondition(ChannelProfileData.url("javascript:alert(1)") == nil && ChannelProfileData.url("https://user:pass@example.com") == nil)
        precondition(ChannelImagePolicy.allowed(URL(string: "https://panels-images.twitch.tv/panel.jpg")!))
        precondition(!ChannelImagePolicy.allowed(URL(string: "https://panels-images.twitch.tv.evil.test/panel.jpg")!))
        let count = backend.calls.count
        let invalid = await model.change(.notifications, setting: "WRONG");precondition(!invalid && backend.calls.count == count)
        for choice in NotificationChoice.allCases {
            let ok = await model.change(.notifications, setting: choice.rawValue)
            precondition(ok && model.relationship?.setting == choice.rawValue)
        }
        let unfollow = await model.change(.unfollow);precondition(unfollow && model.relationship?.followed == false)
        let blocked = await model.change(.notifications, setting: "ALWAYS");precondition(!blocked)
        let follow = await model.change(.follow);precondition(follow && model.relationship?.followed == true)
        backend.stale = true;let stale = await model.change(.unfollow);precondition(!stale && model.relationship?.followed == true && model.error != nil)
        precondition(rejections == [.unfollow], "Unconfirmed mutation reports only its numeric operation")
        backend.stale = false;backend.during = { valid = false }
        await model.load();precondition(changes == 6)
        let invalidCount = backend.calls.count;let lost = await model.change(.unfollow)
        precondition(!lost && backend.calls.count == invalidCount)
        backend.during = nil;valid = true;backend.failing = true;await model.load();precondition(model.error != nil)
        backend.failing = false;backend.malformed = true;await model.load()
        precondition(rejections == [.unfollow, .profile] && model.error != nil, "Malformed metadata records a bounded presentation rejection")
        print("PROFILE_MODEL PASS: profile, panels, safe URLs, follow state, four notification values, verified mutations, stale response and account-loss guards")
    }
}
