import SwiftUI
import UIKit

private final class PanelImageFixtureProtocol: URLProtocol, @unchecked Sendable {
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        let fixturePaths = [
            "https://panels.twitch.tv/panel-fixture",
            "https://static-cdn.jtvnw.net/jtv_user_pictures/fixture-profile_image-70x70.png",
            "https://static-cdn.jtvnw.net/jtv_user_pictures/fixture-profile_image-600x600.png",
            "https://static-cdn.jtvnw.net/jtv_user_pictures/fixture-banner.png"
        ]
        guard let url = request.url, fixturePaths.contains(url.absoluteString),
              let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1",
                                             headerFields: ["Content-Type": "image/png"]),
              let data = Data(base64Encoded: "iVBORw0KGgoAAAANSUhEUgAAACAAAAAwCAIAAAD/zu84AAAALklEQVR4nO3NQQkAAAgEsEtnPxNrCh/CYP+la05FIBAIBAKBQCAQCAQCgUDwKVi88QSmGj03zQAAAABJRU5ErkJggg==") else {
            client?.urlProtocol(self, didFailWithError: URLError(.resourceUnavailable))
            return
        }
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data)
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}

@MainActor private final class ProfileFixtureBackend: ChannelProfileBackend {
    let relationshipUnavailable = ProcessInfo.processInfo.arguments.contains("--profile-relationship-failure")
    var followed = true
    var setting = "PERSONALIZED"
    func request(channelID: String, operation: ProfileOperation, setting: String) async throws -> [String: Any] {
        switch operation {
        case .profile:
            let socials = (1...5).map { index in
                ["title": "Fixture social link \(index)", "url": "https://example.invalid/social-\(index)"]
            }
            var user: [String: Any] = ["displayName": "Profile fixture", "description": "Fixture biography", "followers": ["totalCount": 123],
            "channel": ["socialMedias": socials],
            "currentUser": ["subscriptionBenefit": ["id": "fixture-benefit"]],
            "panels": [NSNull(), ["__typename": "DefaultPanel", "title": "Fixture panel",
                "description": "## Panel notes\n\n[About panel body](https://example.invalid/credits)",
                "imageURL": "https://panels-images.twitch.tv/panel-fixture",
                "linkURL": "https://example.invalid/artwork"]] as [Any]]
            if ProcessInfo.processInfo.arguments.contains("--profile-artwork") {
                user["profileImageURL"] = "https://static-cdn.jtvnw.net/jtv_user_pictures/fixture-profile_image-70x70.png"
                user["bannerImageURL"] = "https://static-cdn.jtvnw.net/jtv_user_pictures/fixture-banner.png"
            }
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
struct ProfileFixture: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> ProfileNavigationController {
        let root = UIHostingController(rootView: AnyView(EmptyView()))
        let navigation = ProfileNavigationController(root: root)
        root.rootView = AnyView(Button("Open fixture profile") { [weak navigation] in
            guard let navigation else { return }
            let profile = UIHostingController(rootView: ProfileFixtureContent(close: { [weak navigation] in
                navigation?.closeProfile()
            }))
            _ = navigation.openProfile(profile)
        })
        return navigation
    }

    func updateUIViewController(_ navigation: ProfileNavigationController, context: Context) {}
}

private struct ProfileFixtureContent: View {
    let close: () -> Void
    @StateObject private var model: ChannelProfileModel
    private let images = ChannelImageCache(protocolClasses: [PanelImageFixtureProtocol.self])
    private let clock = StreamClock()
    @State private var openedLink = ""
    @State private var openCount = 0
    init(close: @escaping () -> Void) {
        self.close = close
        var channel = FollowedChannel(username: "fixture", displayName: "Profile fixture")
        channel.channelID = "123"
        channel.isLive = true
        channel.category = "A long live category name that must wrap inside the profile viewport"
        channel.viewerCount = 75_231
        channel.title = "Fixture stream title"
        _model = StateObject(wrappedValue: ChannelProfileModel(channel: channel, backend: ProfileFixtureBackend(), valid: { true }))
    }
    var body: some View {
        ChannelProfileView(model: model, images: images, clock: clock, close: close) {
            Color.indigo.aspectRatio(16.0 / 9.0, contentMode: .fit)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("Fixture live preview")
                .accessibilityIdentifier("profile.fixture-preview")
        }
        .environment(\.openURL, OpenURLAction { url in
            openCount += 1
            openedLink = "Opened \(openCount): \(url.absoluteString)"
            return .handled
        })
        .overlay(alignment: .topTrailing) {
            if !openedLink.isEmpty {
                Text(openedLink).font(.caption2)
                    .accessibilityIdentifier("profile.opened-link").allowsHitTesting(false)
            }
        }
    }
}
