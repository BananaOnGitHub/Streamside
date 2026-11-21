import SwiftUI
import UIKit

private final class PanelImageFixtureProtocol: URLProtocol, @unchecked Sendable {
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        guard let url = request.url, url.absoluteString == "https://panels.twitch.tv/panel-fixture",
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
            let user: [String: Any] = ["displayName": "Profile fixture", "description": "Fixture biography", "followers": ["totalCount": 123],
            "currentUser": ["subscriptionBenefit": ["id": "fixture-benefit"]],
            "panels": [NSNull(), ["__typename": "DefaultPanel", "title": "Fixture panel",
                "description": "[About panel body](https://example.invalid/credits)",
                "imageURL": "https://panels-images.twitch.tv/panel-fixture",
                "linkURL": "https://example.invalid/artwork"]] as [Any]]
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
    private let images = ChannelImageCache(protocolClasses: [PanelImageFixtureProtocol.self])
    private let clock = StreamClock()
    @State private var closed = false
    @State private var openedLink = ""
    @State private var openCount = 0
    init() {
        var channel = FollowedChannel(username: "fixture", displayName: "Profile fixture")
        channel.channelID = "123"
        channel.isLive = true
        channel.category = "A long live category name that must wrap inside the profile viewport"
        channel.viewerCount = 75_231
        channel.title = "Fixture stream title"
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
}
