import SwiftUI
import UIKit

struct ChannelProfileView<Video: View>: View {
    @ObservedObject var model: ChannelProfileModel
    let images: ChannelImageCache
    let clock: StreamClock
    let close: () -> Void
    let video: () -> Video
    @State private var unfollow = false
    @State private var notifications = false
    @State private var subscription = false
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    private var channel: FollowedChannel { model.channel }
    private var actionBackground: some ShapeStyle {
        reduceTransparency ? AnyShapeStyle(Color(uiColor: .secondarySystemBackground)) : AnyShapeStyle(.regularMaterial)
    }
    var body: some View {
        GeometryReader { geometry in
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    banner(width: geometry.size.width, height: 190 + geometry.safeAreaInsets.top)
                    VStack(alignment: .leading, spacing: 16) {
                        identity.padding(.top, -42)
                        biography
                        actionBar
                        Picker("Profile page", selection: $model.tab) { Text("Home").tag(0); Text("About").tag(1) }
                            .pickerStyle(.segmented).accessibilityIdentifier("profile.tabs")
                        if model.busy { ProgressView().frame(maxWidth: .infinity) }
                        if let error = model.error {
                            Text(error).foregroundStyle(.secondary)
                            Button("Retry profile") { Task { await model.load() } }
                        }
                        page
                    }.padding(.horizontal, 20)
                        .frame(width: geometry.size.width, alignment: .leading)
                }.frame(width: geometry.size.width, alignment: .leading).padding(.bottom, 24)
            }.ignoresSafeArea(edges: .top)
                .overlay(alignment: .topLeading) {
                    Button(action: close) { Image(systemName: "chevron.left").font(.headline).frame(width: 36, height: 36) }
                        .modifier(ProfileGlass()).padding(.leading, 16).padding(.top, 6).accessibilityLabel("Close profile")
                }
        }.background(Color(uiColor: .systemBackground)).tint(.purple)
            .task { await model.load() }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.didBecomeActiveNotification)) { _ in Task { await model.load() } }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)) { _ in unfollow = false; notifications = false; subscription = false }
    }
    private func banner(width: CGFloat, height: CGFloat) -> some View {
        Color(uiColor: .secondarySystemBackground)
            .frame(width: width, height: height)
            .overlay {
                RemoteChannelImage(url: model.data?.banner, images: images, generation: 0)
            }
            .overlay(alignment: .bottom) {
                if !reduceTransparency {
                    Rectangle().fill(.ultraThinMaterial)
                        .mask { LinearGradient(colors: [.clear, .white], startPoint: .top, endPoint: .bottom) }
                        .frame(height: 56)
                }
            }
            .overlay(alignment: .bottom) {
                LinearGradient(colors: [.clear, Color(uiColor: .systemBackground)], startPoint: .top, endPoint: .bottom)
                    .frame(height: 42)
            }
            .clipped()
            .allowsHitTesting(false)
            .accessibilityHidden(true)
    }
    private var identity: some View {
        HStack(spacing: 12) {
            RemoteChannelImage(url: model.data?.avatar ?? channel.avatarURL, images: images, generation: 0, avatar: true)
                .frame(width: 76, height: 76).clipShape(Circle())
                .overlay { if channel.isLive { LiveRing(clock: clock) } }
            VStack(alignment: .leading, spacing: 5) {
                VerifiedChannelName(channel: channel).font(.title2.bold())
                if channel.isLive {
                    Label("Live", systemImage: "dot.radiowaves.left.and.right")
                        .font(.subheadline).foregroundStyle(.red)
                } else { Text("Offline").foregroundStyle(.secondary) }
            }
        }
    }
    @ViewBuilder private var biography: some View {
        if let data = model.data {
            if !data.bio.isEmpty { Text(data.bio).font(.subheadline).textSelection(.enabled) }
            if !data.links.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 14) {
                        ForEach(data.links) { item in
                            Link(destination: item.url) {
                                Label { Text(item.title) } icon: { ProfileSocialIcon(platform: item.platform) }
                            }
                        }
                    }
                }.font(.subheadline)
            }
        }
    }
    private var actionBar: some View {
        HStack(spacing: 10) {
            if let followers = model.data?.followers {
                Text("\(followers.formatted()) followers")
                    .font(.subheadline).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("profile.followers")
            }
            Spacer(minLength: 0)
            followControl
            notificationControl
            subscriptionControl
        }
    }
    private var subscriptionControl: some View {
        Button { subscription = true } label: {
            Image(systemName: model.data?.subscribed == true ? "star.fill" : "star")
                .font(.body.weight(.semibold))
                .frame(width: 48, height: 44)
                .background(Color(uiColor: .secondarySystemBackground), in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Subscription")
        .accessibilityValue(model.data?.subscribed.map { $0 ? "Subscribed" : "Not subscribed" } ?? "Status unavailable")
        .popover(isPresented: $subscription, arrowEdge: .top) {
            Link(destination: URL(string: "https://www.twitch.tv/subscriptions")!) {
                Label("Manage on Twitch", systemImage: "arrow.up.right")
                    .font(.subheadline.weight(.medium)).padding(16)
            }
            .presentationCompactAdaptation(.popover)
            .presentationBackground(Color(uiColor: .secondarySystemBackground))
        }
    }
    private var followControl: some View {
        Button {
            if model.relationship?.followed == true { unfollow = true }
            else { Task { _ = await model.change(.follow) } }
        } label: {
            Image(systemName: model.relationship?.followed == true ? "heart.fill" : "heart").frame(width: 38, height: 32)
        }.modifier(ProfileGlass())
            .disabled(model.busy || model.relationship == nil || (model.relationship?.followed == false && model.relationship?.canFollow == false))
            .accessibilityLabel(model.relationship?.followed == true ? "Following" : "Follow")
            .popover(isPresented: $unfollow, arrowEdge: .top) {
                VStack(alignment: .leading, spacing: 14) {
                    Text("Are you sure you want to unfollow?").font(.subheadline)
                    Button("Unfollow", role: .destructive) { unfollow = false; Task { _ = await model.change(.unfollow) } }
                        .accessibilityIdentifier("profile.unfollow-confirm")
                }.padding(18).presentationCompactAdaptation(.popover).presentationBackground(.regularMaterial)
            }
    }
    private var notificationControl: some View {
        Button { notifications = true } label: {
            Image(systemName: NotificationChoice(rawValue: model.relationship?.setting ?? "")?.icon ?? "bell").frame(width: 38, height: 32)
        }.modifier(ProfileGlass()).disabled(model.busy || model.relationship?.followed != true)
            .accessibilityLabel("Channel notifications")
            .popover(isPresented: $notifications, arrowEdge: .top) {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(NotificationChoice.allCases) { choice in
                        Button {
                            notifications = false; Task { _ = await model.change(.notifications, setting: choice.rawValue) }
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: choice.icon).frame(width: 24)
                                Text(choice.title); Spacer()
                                if model.relationship?.setting == choice.rawValue { Image(systemName: "checkmark") }
                            }.padding(.vertical, 13).contentShape(Rectangle())
                        }.buttonStyle(.plain)
                    }
                }.padding(.horizontal, 18).frame(width: 260).presentationCompactAdaptation(.popover).presentationBackground(.regularMaterial)
            }
    }
    private var streamDetails: String {
        [channel.category.isEmpty ? nil : channel.category,
         channel.viewerCount.map { $0 == 1 ? "1 viewer" : "\($0.formatted()) viewers" }]
            .compactMap { $0 }.joined(separator: " · ")
    }
    @ViewBuilder private var page: some View {
        if model.tab == 0 {
            if channel.isLive {
                Text("Live").font(.title3.bold()); video()
                VStack(alignment: .leading, spacing: 5) {
                    Text(channel.title).font(.subheadline).fixedSize(horizontal: false, vertical: true)
                    if !streamDetails.isEmpty {
                        Text(streamDetails).font(.subheadline).foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                            .accessibilityIdentifier("profile.stream-details")
                    }
                }
                if !channel.tags.isEmpty { AllStreamTags(tags: channel.tags) }
                if !channel.playbackAllowed { Text("Twitch does not currently allow this account to watch this stream.").font(.footnote) }
            } else { Text("This channel is offline.").foregroundStyle(.secondary) }
        } else if let panels = model.data?.panels {
            if panels.isEmpty {
                Text("No channel panels.").foregroundStyle(.secondary)
                aboutWebLink
            }
            ForEach(panels) { panel in
                VStack(alignment: .leading, spacing: 10) {
                    if !panel.title.isEmpty { Text(panel.title).font(.headline) }
                    if let url = panel.image {
                        ProfilePanelArtwork(url: url, images: images)
                    }
                    if panel.supported {
                        if !panel.text.isEmpty { Text(panel.text).font(.subheadline).textSelection(.enabled) }
                        if let url = panel.link { Link("Open panel link", destination: url) }
                    } else { Text("Interactive panels are not supported yet.").font(.footnote).foregroundStyle(.secondary) }
                }.padding(16).frame(maxWidth: .infinity, alignment: .leading)
                    .background(actionBackground, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            }
        } else if !model.busy, model.data != nil {
            Text("Channel panels could not be loaded.").foregroundStyle(.secondary)
            Button("Retry panels") { Task { await model.load() } }
            aboutWebLink
        }
    }
    @ViewBuilder private var aboutWebLink: some View {
        if let url = StreamShareLink.url(username: channel.username)?.appendingPathComponent("about") {
            Link(destination: url) { Label("Open About on Twitch", systemImage: "arrow.up.right") }
        }
    }
}
private struct ProfilePanelArtwork: View {
    let url: URL
    let images: ChannelImageCache
    @State private var image: UIImage?
    @State private var failed = false

    var body: some View {
        Group {
            if let image {
                Image(uiImage: image).resizable().scaledToFit()
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .accessibilityLabel("Panel image")
                    .accessibilityIdentifier("profile.panel-image")
            } else if failed {
                Label("Panel image unavailable", systemImage: "photo")
                    .font(.footnote).foregroundStyle(.secondary)
            } else {
                ProgressView().accessibilityLabel("Loading panel image")
            }
        }
        .frame(maxWidth: 360)
        .task(id: url) {
            image = nil
            failed = false
            let result = await images.load(url: url, generation: 0, avatar: false)
            guard !Task.isCancelled else { return }
            image = result
            failed = result == nil
        }
    }
}

private struct ProfileGlass: ViewModifier {
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @ViewBuilder func body(content: Content) -> some View {
        if reduceTransparency { content.padding(6).background(Color(uiColor: .secondarySystemBackground), in: Capsule()) }
        else if #available(iOS 26.0, *) { content.padding(6).glassEffect(.regular.interactive(), in: Capsule()) }
        else { content.padding(6).background(.regularMaterial, in: Capsule()) }
    }
}

private final class ProfileSocialBundle: NSObject {}

private struct ProfileSocialIcon: View {
    let platform: ProfileSocialPlatform?

    var body: some View {
        if let platform, let image = Self.artwork[platform] {
            Image(uiImage: image).renderingMode(.template).resizable().scaledToFit()
                .frame(width: 16, height: 16).foregroundStyle(color(platform))
        } else { Image(systemName: "link") }
    }
    private static let artwork: [ProfileSocialPlatform: UIImage] = {
        let bundle = Bundle(for: ProfileSocialBundle.self)
        var images: [ProfileSocialPlatform: UIImage] = [:]
        for platform in ProfileSocialPlatform.allCases {
            if let url = bundle.url(forResource: "profile-social-" + platform.rawValue, withExtension: "png"),
               let image = UIImage(contentsOfFile: url.path) { images[platform] = image }
        }
        return images
    }()
    private func color(_ platform: ProfileSocialPlatform) -> Color {
        switch platform {
        case .twitter: return Color(red: 0.11, green: 0.63, blue: 0.95)
        case .x, .tiktok: return .primary
        case .youtube: return Color(red: 1, green: 0.16, blue: 0.18)
        case .instagram: return Color(red: 0.89, green: 0.25, blue: 0.50)
        case .discord: return Color(red: 0.42, green: 0.46, blue: 1)
        case .facebook: return Color(red: 0.26, green: 0.55, blue: 1)
        case .twitch: return Color(red: 0.65, green: 0.39, blue: 1)
        }
    }
}
