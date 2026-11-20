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
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)) { _ in unfollow = false; notifications = false }
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
                    Label("Live · " + channel.category + (channel.viewerCount.map { " · " + $0.formatted() + " viewers" } ?? ""),
                          systemImage: "dot.radiowaves.left.and.right")
                        .font(.subheadline).foregroundStyle(.red).lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                } else { Text("Offline").foregroundStyle(.secondary) }
            }
        }
    }
    @ViewBuilder private var biography: some View {
        if let data = model.data {
            if !data.bio.isEmpty { Text(data.bio).font(.subheadline).textSelection(.enabled) }
            if let followers = data.followers { Text("\(followers.formatted()) followers").foregroundStyle(.secondary) }
            if !data.links.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 14) {
                        ForEach(data.links) { item in Link(destination: item.url) { Label(item.title, systemImage: "link") } }
                    }
                }.font(.subheadline)
            }
        }
    }
    private var actionBar: some View {
        HStack(spacing: 12) {
            followControl
            notificationControl
            Button {} label: {
                Label("Subscribe", systemImage: "star").lineLimit(1).minimumScaleFactor(0.75)
                    .frame(maxWidth: .infinity, minHeight: 30)
            }
                .modifier(ProfileGlass()).disabled(true).accessibilityHint("Not available in this prototype")
        }
    }
    private var followControl: some View {
        Button {
            if model.relationship?.followed == true { unfollow = true }
            else { Task { _ = await model.change(.follow) } }
        } label: {
            Image(systemName: model.relationship?.followed == true ? "heart.fill" : "heart").frame(width: 54, height: 30)
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
            Image(systemName: NotificationChoice(rawValue: model.relationship?.setting ?? "")?.icon ?? "bell").frame(width: 54, height: 30)
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
    @ViewBuilder private var page: some View {
        if model.tab == 0 {
            if channel.isLive {
                Text("Live").font(.title3.bold()); video()
                Text(channel.title).font(.subheadline).fixedSize(horizontal: false, vertical: true)
                if !channel.tags.isEmpty { AllStreamTags(tags: channel.tags) }
                if !channel.playbackAllowed { Text("Twitch does not currently allow this account to watch this stream.").font(.footnote) }
            } else { Text("This channel is offline.").foregroundStyle(.secondary) }
        } else if let data = model.data {
            if data.panels.isEmpty { Text("No channel panels.").foregroundStyle(.secondary) }
            ForEach(data.panels) { panel in
                VStack(alignment: .leading, spacing: 10) {
                    if !panel.title.isEmpty { Text(panel.title).font(.headline) }
                    if panel.image != nil {
                        Color.clear.frame(height: 150)
                            .overlay { RemoteChannelImage(url: panel.image, images: images, generation: 0) }
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    if panel.supported {
                        if !panel.text.isEmpty { Text(panel.text).font(.subheadline).textSelection(.enabled) }
                        if let url = panel.link { Link("Open panel link", destination: url) }
                    } else { Text("Interactive panels are not supported yet.").font(.footnote).foregroundStyle(.secondary) }
                }.padding(16).frame(maxWidth: .infinity, alignment: .leading)
                    .background(actionBackground, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            }
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
