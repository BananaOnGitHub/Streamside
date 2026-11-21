import Foundation

@MainActor private final class FixtureBackend: ChannelProfileBackend {
    var followed = true, stale = false, failing = false, malformed = false
    var setting = "PERSONALIZED"
    var relationshipUnavailable = false
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
            if relationshipUnavailable { throw CocoaError(.coderReadCorrupt) }
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
        precondition(model.data?.panels?.count == 2 && model.data?.panels?[0].supported == true && model.data?.panels?[1].supported == false)
        precondition(model.relationship?.followed == true && model.relationship?.setting == "PERSONALIZED")
        let credits = ChannelProfileData.Panel(id: 0, row: [
            "__typename": "DefaultPanel",
            "description": "Credits\n\nModel Art: [Artist](https://bsky.app/profile/artist.bsky.social)\n"
                + "Rig: [rig_fixture](https://x.com/rig_fixture)\n"
                + "[Local](file:///tmp/owned) [Relative](/local) [Custom](custom://open) [Credentials](https://user:pass@example.com)",
            "linkURL": "https://example.com/panel"
        ])
        precondition(String(credits.text.characters) == "Credits\n\nModel Art: Artist\nRig: rig_fixture\nLocal Relative Custom Credentials")
        precondition(credits.text.runs.compactMap { $0.link?.absoluteString } == [
            "https://bsky.app/profile/artist.bsky.social", "https://x.com/rig_fixture"
        ])
        precondition(credits.link?.absoluteString == "https://example.com/panel")
        let subscribed: [String: Any] = ["displayName": "Fixture", "currentUser": ["subscriptionBenefit": ["id": "fixture-benefit"]]]
        let unsubscribed: [String: Any] = ["displayName": "Fixture", "currentUser": ["subscriptionBenefit": NSNull()], "panels": [] as [Any]]
        let subscribedProfile = ChannelProfileData(result: ["user": subscribed])
        let unsubscribedProfile = ChannelProfileData(result: ["user": unsubscribed])
        precondition(subscribedProfile?.subscribed == true && subscribedProfile?.panels == nil)
        precondition(unsubscribedProfile?.subscribed == false && unsubscribedProfile?.panels?.isEmpty == true)
        precondition(model.data?.subscribed == nil, "Missing account data is not an unsubscribed status")
        let xURL = URL(string: "https://x.com/fixture")!
        precondition(ProfileSocialPlatform(url: xURL, title: "Twitter") == .twitter)
        precondition(ProfileSocialPlatform(url: xURL, title: "Follow me on X") == .x)
        precondition(ProfileSocialPlatform(url: xURL, title: "Social") == .twitter)
        precondition(ProfileSocialPlatform(url: URL(string: "https://youtu.be/fixture")!, title: "Video") == .youtube)
        precondition(ProfileSocialPlatform(url: URL(string: "https://discord.com.example.org/fixture")!, title: "Discord") == nil)
        precondition(ChannelProfileData.url("javascript:alert(1)") == nil && ChannelProfileData.url("https://user:pass@example.com") == nil)
        precondition(ChannelImagePolicy.allowed(URL(string: "https://panels-images.twitch.tv/panel.jpg")!))
        precondition(!ChannelImagePolicy.allowed(URL(string: "https://panels-images.twitch.tv.evil.test/panel.jpg")!))
        let panelURL = URL(string: "https://panels.twitch.tv/panel-fixture")!
        precondition(ChannelImagePolicy.allowed(panelURL))
        precondition(ChannelImagePolicy.panelURL(panelURL) == panelURL)
        precondition(ChannelImagePolicy.panelURL(URL(string: "https://panels-images.twitch.tv/panel-fixture")!) == panelURL)
        for invalid in ["https://panels.twitch.tv.evil.test/image", "http://panels.twitch.tv/image",
                        "https://user@panels.twitch.tv/image", "https://panels.twitch.tv:8443/image"] {
            precondition(ChannelImagePolicy.panelURL(URL(string: invalid)!) == nil)
        }
        backend.relationshipUnavailable = true
        await model.load()
        precondition(model.data?.bio == "Bio" && model.data?.panels?.count == 2)
        precondition(model.relationship == nil && model.error == "Follow and notification settings could not be loaded.")
        let requestCount = backend.calls.count
        let unavailableChange = await model.change(.unfollow)
        precondition(!unavailableChange && backend.calls.count == requestCount)
        backend.relationshipUnavailable = false
        await model.load()
        precondition(model.error == nil && model.relationship?.followed == true)
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
        print("PROFILE_MODEL PASS: profile, panels, Markdown links, safe URLs, follow state, four notification values, verified mutations, stale response and account-loss guards")
    }
}
