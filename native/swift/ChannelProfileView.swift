import SwiftUI
import UIKit

struct ChannelProfileView<Video: View>: View {
    @ObservedObject var model: ChannelProfileModel
    let images: ChannelImageCache
    let clock: StreamClock
    let close: () -> Void
    var onTabSettled: (Int) -> Void = { _ in }
    let video: () -> Video
    @AppStorage(ProfileAccent.sourceKey) private var storedAccent = ProfileAccentSource.banner.rawValue
    @AppStorage(ProfileAccent.manualKey) private var manualAccent = ProfileAccent.defaultManual
    @State private var bannerAccent: UInt32?
    @State private var avatarAccent: UInt32?
    @State private var unfollow = false
    @State private var notifications = false
    @State private var subscription = false
    @State private var artworkFile: ProfileArtworkFile?
    @State private var artworkViewerActive = false
    @State private var pageDrag: CGFloat = 0
    @State private var swipeExclusions = ProfileSwipeExclusions()
    @State private var hasVisitedAbout = false
    @State private var tabGeneration = 0
    @State private var settleTask: Task<Void, Never>?
    @Environment(\.layoutDirection) private var layoutDirection
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    private var channel: FollowedChannel { model.channel }
    private var accent: Color {
        let source = ProfileAccentSource(rawValue: storedAccent) ?? .banner
        return ProfileAccent.color(source.rgb(banner: bannerAccent, avatar: avatarAccent, manual: manualAccent))
    }
    private var actionBackground: some ShapeStyle {
        reduceTransparency ? AnyShapeStyle(Color(uiColor: .secondarySystemBackground)) : AnyShapeStyle(.regularMaterial)
    }
    var body: some View {
        GeometryReader { geometry in
            let previewSize = panelPreviewSize(in: geometry.size)
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    banner(width: geometry.size.width, height: 190 + geometry.safeAreaInsets.top,
                           previewSize: previewSize)
                    VStack(alignment: .leading, spacing: 16) {
                        identity(previewSize: previewSize).padding(.top, -42)
                        biography(previewSize: previewSize)
                        actionBar
                        Picker("Profile page", selection: Binding(get: { model.tab }, set: selectTab)) {
                            Text("Home").tag(0); Text("About").tag(1)
                        }
                            .pickerStyle(.segmented).accessibilityIdentifier("profile.tabs")
                        if model.busy { ProgressView().frame(maxWidth: .infinity) }
                        if let error = model.error {
                            Text(error).foregroundStyle(.secondary)
                            Button("Retry profile") { Task { await model.load() } }
                        }
                        pages(width: max(1, geometry.size.width - 40), previewSize: previewSize)
                    }.padding(.horizontal, 20)
                        .frame(width: geometry.size.width, alignment: .leading)
                }.frame(width: geometry.size.width, alignment: .leading).padding(.bottom, 24)
            }.ignoresSafeArea(edges: .top)
                .background {
                    ProfileTabSwipe(exclusions: swipeExclusions) { event in
                        trackTabSwipe(event, width: max(1, geometry.size.width - 40))
                    }
                }
                .overlay(alignment: .topLeading) {
                    if !artworkViewerActive {
                        Button {
                            if !artworkViewerActive { close() }
                        } label: {
                            Image(systemName: "chevron.left").font(.headline).frame(width: 36, height: 36)
                        }
                        .modifier(ProfileGlass()).padding(.leading, 16).padding(.top, 6)
                        .accessibilityLabel("Close profile")
                    }
                }
        }.background(Color(uiColor: .systemBackground)).tint(accent)
            .fullScreenCover(item: $artworkFile, onDismiss: { artworkViewerActive = false }) { file in
                ProfileArtworkViewer(file: file)
            }
            .task { await model.load() }
            .onDisappear { invalidateTabSettlement() }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.didBecomeActiveNotification)) { _ in Task { await model.load() } }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)) { _ in unfollow = false; notifications = false; subscription = false }
    }
    private func openArtwork(_ file: ProfileArtworkFile) {
        guard !artworkViewerActive else { return }
        // Unmount the glass control until the cover has finished dismissing.
        artworkViewerActive = true
        artworkFile = file
    }

    private func banner(width: CGFloat, height: CGFloat, previewSize: CGSize) -> some View {
        Color(uiColor: .secondarySystemBackground)
            .frame(width: width, height: height)
            .overlay {
                RemoteChannelImage(url: model.data?.banner, images: images, generation: 0,
                    artworkAccent: { bannerAccent = $0 }).allowsHitTesting(false)
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
            .contentShape(Rectangle())
            .modifier(ProfileArtworkMenu(url: model.data?.banner, kind: .banner, images: images,
                                         previewSize: previewSize, presentViewer: openArtwork))
    }
    private func identity(previewSize: CGSize) -> some View {
        let avatar = model.data?.avatar ?? channel.avatarURL
        return HStack(spacing: 12) {
            RemoteChannelImage(url: avatar, images: images, generation: 0, avatar: true,
                artworkAccent: { avatarAccent = $0 })
                .frame(width: 76, height: 76).clipShape(Circle())
                .contentShape(Circle())
                .contentShape(.contextMenuPreview, Circle())
                .modifier(ProfileArtworkMenu(url: avatar, kind: .avatar, images: images,
                                             previewSize: previewSize, presentViewer: openArtwork))
                .overlay { if channel.isLive { LiveRing(clock: clock).allowsHitTesting(false) } }
            VStack(alignment: .leading, spacing: 5) {
                VerifiedChannelName(channel: channel).font(.title2.bold())
                if channel.isLive {
                    Label("Live", systemImage: "dot.radiowaves.left.and.right")
                        .font(.subheadline).foregroundStyle(.red)
                } else { Text("Offline").foregroundStyle(.secondary) }
            }
        }
    }
    @ViewBuilder private func biography(previewSize: CGSize) -> some View {
        if let data = model.data {
            if !data.bio.isEmpty { Text(data.bio).font(.subheadline).textSelection(.enabled) }
            if !data.links.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 14) {
                        ForEach(data.links) { item in
                            ProfileSocialLink(item: item, accent: accent, previewSize: previewSize)
                        }
                    }
                }
                .font(.subheadline)
                .background { ProfileSocialLinksRegion(exclusions: swipeExclusions) }
                .accessibilityIdentifier("profile.social-links")
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
                .foregroundStyle(accent)
                .frame(width: 48, height: 44)
                .contentShape(Rectangle())
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
    private func panelPreviewSize(in viewport: CGSize) -> CGSize {
        let width = max(1, min(460, viewport.width - 32))
        return CGSize(width: width, height: max(1, min(width * 1.42, viewport.height - 104)))
    }

    private func pages(width: CGFloat, previewSize: CGSize) -> some View {
        ProfileTabPages(selection: model.tab,
                        position: min(1, max(0, CGFloat(model.tab) - pageDrag / width))) {
            VStack(alignment: .leading, spacing: 16) { homePage }
                .allowsHitTesting(model.tab == 0).accessibilityHidden(model.tab != 0)
            VStack(alignment: .leading, spacing: 16) {
                aboutPage(previewSize: previewSize)
            }
            .allowsHitTesting(model.tab == 1).accessibilityHidden(model.tab != 1)
        }
        .frame(width: width, alignment: .leading)
        .clipped()
    }

    private func trackTabSwipe(_ event: ProfileTabSwipe.Event, width: CGFloat) {
        let direction: CGFloat = layoutDirection == .rightToLeft ? -1 : 1
        switch event {
        case .began(let distance):
            invalidateTabSettlement()
            pageDrag = distance * direction
        case .changed(let distance):
            pageDrag = distance * direction
        case .ended(let distance, let velocity):
            let towardOther = (model.tab == 0 ? -direction : direction)
            let travel = distance * towardOther
            let projected = travel + velocity * towardOther * 0.12
            let commit = travel > width * 0.34 || (travel > 24 && projected > width * 0.5)
            selectTab(commit ? 1 - model.tab : model.tab)
        case .cancelled:
            selectTab(model.tab)
        }
    }

    private func selectTab(_ tab: Int) {
        invalidateTabSettlement()
        let generation = tabGeneration
        let update = { model.tab = tab; pageDrag = 0 }
        let settled = {
            guard generation == tabGeneration, model.tab == tab else { return }
            if tab == 1 { hasVisitedAbout = true }
            onTabSettled(tab)
        }
        if #available(iOS 17, *), !reduceMotion {
            withAnimation(.spring(response: 0.34, dampingFraction: 0.9), completionCriteria: .removed) {
                update()
            } completion: {
                // Start/stop can synchronously touch the native media view.
                // Keep that work out of the page's animation transaction.
                DispatchQueue.main.async { settled() }
            }
        } else {
            let duration = reduceMotion ? 0.0 : 0.32
            withAnimation(reduceMotion ? nil : .easeOut(duration: duration), update)
            settleTask = Task { @MainActor in
                do { try await Task.sleep(nanoseconds: UInt64((duration + 0.03) * 1_000_000_000)) }
                catch { return }
                settled()
            }
        }
    }

    private func invalidateTabSettlement() {
        tabGeneration &+= 1
        settleTask?.cancel()
        settleTask = nil
    }

    @ViewBuilder private var homePage: some View {
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
    }

    @ViewBuilder private func aboutPage(previewSize: CGSize) -> some View {
        if let panels = model.data?.panels {
            if panels.isEmpty {
                Text("No channel panels.").foregroundStyle(.secondary)
                aboutWebLink
            }
            ForEach(panels) { panel in
                VStack(alignment: .leading, spacing: 10) {
                    if !panel.title.isEmpty { Text(panel.title).font(.headline) }
                    if let url = panel.image {
                        ProfilePanelArtwork(url: url, link: panel.supported ? panel.link : nil,
                            title: panel.title, images: images, previewSize: previewSize, loadArtwork: hasVisitedAbout)
                    }
                    if panel.supported {
                        if !panel.text.blocks.isEmpty { PanelMarkdownView(markdown: panel.text, previewSize: previewSize, accent: accent) }
                        if panel.image == nil, let link = panel.link { Link("Open panel link", destination: link) }
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
    let link: URL?
    let title: String
    let images: ChannelImageCache
    let previewSize: CGSize
    let loadArtwork: Bool
    @State private var image: UIImage?
    @State private var failed = false

    var body: some View {
        Group {
            if let image {
                let artwork = Image(uiImage: image).resizable().scaledToFit()
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                if let link {
                    LinkedPanelImage(image: image, url: link, title: title, previewSize: previewSize)
                } else {
                    artwork.accessibilityLabel("Panel image").accessibilityIdentifier("profile.panel-image")
                }
            } else if failed {
                if let link { Link("Open panel link", destination: link) }
                else {
                    Label("Panel image unavailable", systemImage: "photo")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            } else {
                ProgressView().accessibilityLabel("Loading panel image")
            }
        }
        .frame(maxWidth: 360)
        .task(id: loadArtwork ? url : nil) {
            image = nil
            failed = false
            guard loadArtwork else { return }
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

private struct ProfileSocialLink: UIViewRepresentable {
    let item: ChannelProfileData.Link
    let accent: Color
    let previewSize: CGSize
    @Environment(\.openURL) private var openURL
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    func makeCoordinator() -> PanelLinkMenu { PanelLinkMenu() }

    func makeUIView(context: Context) -> UIButton {
        let button = UIButton(type: .system)
        let menu = context.coordinator
        button.addInteraction(UIContextMenuInteraction(delegate: menu))
        button.addAction(UIAction { [weak menu] _ in
            guard let menu, let url = menu.destination(.zero) else { return }
            menu.open(url)
        }, for: .touchUpInside)
        button.accessibilityTraits = .link
        return button
    }

    func updateUIView(_ button: UIButton, context: Context) {
        let url = item.url
        let openURL = openURL
        context.coordinator.destination = { _ in url }
        context.coordinator.open = { openURL($0) }
        context.coordinator.previewSize = previewSize
        var configuration = UIButton.Configuration.plain()
        let trait = UITraitCollection(preferredContentSizeCategory: UIContentSizeCategory(dynamicTypeSize))
        let title = NSAttributedString(string: item.title, attributes: [
            .font: UIFont.preferredFont(forTextStyle: .subheadline, compatibleWith: trait)
        ])
        if let formattedTitle = try? AttributedString(title, including: \.uiKit) {
            configuration.attributedTitle = formattedTitle
        } else {
            configuration.title = item.title
        }
        configuration.contentInsets = NSDirectionalEdgeInsets(top: 3, leading: 0, bottom: 3, trailing: 0)
        configuration.imagePadding = 5
        configuration.baseForegroundColor = UIColor(accent)
        if let platform = item.platform, let image = Self.artwork[platform] {
            configuration.image = image
            let tint = color(platform)
            configuration.imageColorTransformer = UIConfigurationColorTransformer { _ in tint }
        } else {
            configuration.image = UIImage(systemName: "link", withConfiguration: UIImage.SymbolConfiguration(textStyle: .subheadline))
        }
        button.configuration = configuration
        button.accessibilityLabel = item.title
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UIButton, context: Context) -> CGSize? {
        uiView.intrinsicContentSize
    }

    private static let artwork: [ProfileSocialPlatform: UIImage] = {
        let bundle = Bundle(for: ProfileSocialBundle.self)
        var images: [ProfileSocialPlatform: UIImage] = [:]
        let size = CGSize(width: 16, height: 16)
        for platform in ProfileSocialPlatform.allCases {
            if let url = bundle.url(forResource: "profile-social-" + platform.rawValue, withExtension: "png"),
               let image = UIImage(contentsOfFile: url.path) {
                images[platform] = UIGraphicsImageRenderer(size: size).image { _ in
                    image.draw(in: CGRect(origin: .zero, size: size))
                }.withRenderingMode(.alwaysTemplate)
            }
        }
        return images
    }()
    private func color(_ platform: ProfileSocialPlatform) -> UIColor {
        switch platform {
        case .twitter: return UIColor(red: 0.11, green: 0.63, blue: 0.95, alpha: 1)
        case .x, .tiktok: return .label
        case .youtube: return UIColor(red: 1, green: 0.16, blue: 0.18, alpha: 1)
        case .instagram: return UIColor(red: 0.89, green: 0.25, blue: 0.50, alpha: 1)
        case .discord: return UIColor(red: 0.42, green: 0.46, blue: 1, alpha: 1)
        case .facebook: return UIColor(red: 0.26, green: 0.55, blue: 1, alpha: 1)
        case .twitch: return UIColor(red: 0.65, green: 0.39, blue: 1, alpha: 1)
        }
    }
}
