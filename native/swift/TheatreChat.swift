import SwiftUI
import UIKit

@MainActor
struct TheatreChat: View {
    let channel: String?
    @State private var status: TwitchGuestChat.Status = .connecting
    @State private var timeline = TwitchChatTimeline()
    @State private var connectionID = UUID()
    @StateObject private var avatars: ChatAvatars

    init(channel: String?, images: ChannelImageCache, resolveAvatar: @escaping ChatAvatars.Resolver) {
        self.channel = channel
        _avatars = StateObject(wrappedValue: ChatAvatars(cache: images, resolve: resolveAvatar))
    }

    var body: some View {
        StreamChatTranscript(timeline: $timeline, statusText: statusText, listening: status == .listening,
                             avatars: avatars.images, requestAvatars: avatars.updateVisible)
            .onAppear { avatars.setActive(channel != nil) }
            .onChange(of: channel) { avatars.setActive($0 != nil) }
            .onDisappear { avatars.setActive(false) }
            .task(id: channel) {
                let id = UUID()
                connectionID = id
                guard let channel else { return }
                await TwitchGuestChat.listen(channel: channel) { update in
                    guard connectionID == id, !Task.isCancelled else { return }
                    switch update {
                    case .status(let next): if next != status { status = next }
                    case .events(let events):
                        withTransaction(Transaction(animation: nil)) { timeline.apply(events) }
                    }
                }
            }
    }

    private var statusText: String {
        if channel == nil { return "Waiting for stream chat…" }
        switch status {
        case .connecting: return "Connecting to chat…"
        case .listening: return "Waiting for messages…"
        case .reconnecting: return "Reconnecting to chat…"
        case .unavailable: return "Chat is unavailable."
        }
    }
}

struct StreamChatTranscript: View {
    @Binding var timeline: TwitchChatTimeline
    let statusText: String
    let listening: Bool
    let avatars: [UInt32: UIImage]
    let requestAvatars: ([UInt32]) -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @GestureState private var legacyDragging = false
    @State private var legacyBottom: CGFloat = 0
    private let bottomTolerance: CGFloat = 12
    private var followTarget: String? { timeline.isPaused ? nil : timeline.messages.last?.id }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Stream chat").font(.footnote.weight(.semibold))
                Spacer()
                if !timeline.messages.isEmpty, !listening {
                    Text(statusText).font(.caption).foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)

            if timeline.messages.isEmpty {
                Text(statusText).font(.footnote).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                trackedScroll
                    .overlay(alignment: .bottom) { catchUpPill }
                    .clipped()
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    @ViewBuilder private var trackedScroll: some View {
        if #available(iOS 18.0, *) {
            transcriptScroll(measureBottom: false)
                .onScrollTargetVisibilityChange(idType: String.self, threshold: 0.1) { visibleRows in
                    let visible = Set(visibleRows)
                    requestAvatars(timeline.messages.reversed().compactMap {
                        visible.contains($0.id) ? $0.userID : nil
                    })
                }
                .modifier(ChatLiveScrollPosition(followTarget: followTarget, bottomTolerance: bottomTolerance,
                                                 pause: { timeline.pause() }, resume: { timeline.resume() }))
        } else {
            ScrollViewReader { reader in
                GeometryReader { viewport in
                    transcriptScroll(measureBottom: true)
                        .coordinateSpace(name: "chat.viewport")
                        .onPreferenceChange(ChatBottomEdge.self) { legacyBottom = $0 }
                        .simultaneousGesture(DragGesture(minimumDistance: 4).updating($legacyDragging) { value, dragging, _ in
                            if abs(value.translation.height) > abs(value.translation.width) { dragging = true }
                        })
                        .onChange(of: legacyDragging) { dragging in
                            if dragging { timeline.pause() }
                            else if legacyBottom - viewport.size.height <= bottomTolerance { timeline.resume() }
                        }
                        .onChange(of: viewport.size.height) { _ in scrollToBottom(reader) }
                }
                .onAppear {
                    scrollToBottom(reader)
                    requestRecentAvatars()
                }
                .onChange(of: followTarget) { _ in
                    scrollToBottom(reader)
                    requestRecentAvatars()
                }
            }
        }
    }

    private func transcriptScroll(measureBottom: Bool) -> some View {
        ScrollView {
            // The transcript is bounded. Measure all rows so the bottom
            // offset is exact even when none of the newest rows are visible.
            rows(measureBottom: measureBottom)
                .padding(.horizontal, 14)
                .padding(.vertical, 4)
                .background {
                    if measureBottom {
                        GeometryReader { geometry in
                            Color.clear.preference(key: ChatBottomEdge.self,
                                value: geometry.frame(in: .named("chat.viewport")).maxY)
                        }
                    }
                }
        }
        .accessibilityIdentifier("chat.transcript")
    }

    @ViewBuilder private func rows(measureBottom: Bool) -> some View {
        if #available(iOS 18.0, *) {
            messageStack(measureBottom: measureBottom).scrollTargetLayout()
        } else {
            messageStack(measureBottom: measureBottom)
        }
    }

    private func messageStack(measureBottom: Bool) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            ForEach(timeline.messages) { message in
                VStack(alignment: .leading, spacing: 5) {
                    if message.id == timeline.firstNewMessageID { unreadMarker }
                    row(message)
                }
                .id(message.id)
            }
            if measureBottom {
                Color.clear.frame(height: 1).id(ChatBottomEdge.target)
                    .accessibilityHidden(true)
            }
        }
    }

    private func requestRecentAvatars() {
        guard !timeline.isPaused else { return }
        requestAvatars(timeline.messages.suffix(24).reversed().compactMap { $0.userID })
    }

    private var catchUpPill: some View {
        let unread = timeline.unreadCount
        return VStack {
            if unread > 0 {
                Button {
                    timeline.resume()
                } label: {
                    pillSurface(unread == 1 ? "1 new message" : "\(unread) new messages")
                }
                .buttonStyle(.plain)
                .contentShape(.interaction, Capsule())
                .accessibilityIdentifier("chat.catch-up")
                .accessibilityHint("Jump to the latest messages")
                .padding(.bottom, 10)
                .transition(reduceMotion ? .opacity : .move(edge: .bottom).combined(with: .opacity))
            }
        }
        .animation(.easeOut(duration: reduceMotion ? 0.16 : 0.24), value: unread > 0)
    }

    @ViewBuilder private func pillSurface(_ title: String) -> some View {
        let label = Label(title, systemImage: "arrow.down")
            .font(.footnote.weight(.semibold))
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .frame(minHeight: 44)
            .contentShape(.interaction, Capsule())
        if reduceTransparency {
            label.background(Color(uiColor: .secondarySystemBackground), in: Capsule())
        } else if #available(iOS 26.0, *) {
            label.glassEffect(.regular.interactive(), in: Capsule())
        } else {
            label.background(.regularMaterial, in: Capsule())
        }
    }

    private var unreadMarker: some View {
        HStack {
            Rectangle().frame(height: 1)
            Text("New messages").font(.caption2.weight(.semibold)).fixedSize()
            Rectangle().frame(height: 1)
        }
        .foregroundStyle(Color.accentColor)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("chat.new-messages")
    }

    private func row(_ message: TwitchChatMessage) -> some View {
        let color = message.color.map { rgb in
            Color(red: Double((rgb >> 16) & 255) / 255,
                  green: Double((rgb >> 8) & 255) / 255,
                  blue: Double(rgb & 255) / 255)
        } ?? .primary
        let author = Text(verbatim: message.author).bold().foregroundColor(color)
        return HStack(alignment: .top, spacing: 6) {
            avatar(message.userID.flatMap { avatars[$0] })
            Text("\(author): \(Text(verbatim: message.body))")
                .font(.subheadline)
                .frame(maxWidth: .infinity, alignment: .leading)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func avatar(_ image: UIImage?) -> some View {
        Circle()
            .fill(Color.secondary.opacity(0.12))
            .frame(width: 18, height: 18)
            .overlay {
                if let image {
                    Image(uiImage: image).resizable().scaledToFill()
                } else {
                    Image(systemName: "person.fill").font(.system(size: 9)).foregroundStyle(.secondary)
                }
            }
            .clipShape(Circle())
            .accessibilityHidden(true)
    }

    private func scrollToBottom(_ reader: ScrollViewProxy) {
        guard followTarget != nil else { return }
        var transaction = Transaction(animation: nil)
        transaction.disablesAnimations = true
        withTransaction(transaction) { reader.scrollTo(ChatBottomEdge.target, anchor: .bottom) }
    }
}

// Scrolling to a row during a viewport resize can align it under the home
// indicator. Position the actual scroll edge so the system includes its insets.
@available(iOS 18.0, *)
private struct ChatLiveScrollPosition: ViewModifier {
    let followTarget: String?
    let bottomTolerance: CGFloat
    let pause: () -> Void
    let resume: () -> Void
    @State private var position = ScrollPosition(idType: String.self, edge: .bottom)
    @State private var latestOffset: CGFloat?
    @State private var userScrolling = false

    func body(content: Content) -> some View {
        content
            .scrollPosition($position)
            .defaultScrollAnchor(.bottom, for: .initialOffset)
            .defaultScrollAnchor(followTarget == nil ? nil : .bottom, for: .sizeChanges)
            .onScrollGeometryChange(for: CGFloat.self, of: Self.bottomOffset) { _, offset in
                latestOffset = offset
                follow(offset)
            }
            .onChange(of: followTarget) { _, _ in
                if let latestOffset { follow(latestOffset) }
            }
            .onScrollPhaseChange { _, phase, context in
                if phase == .interacting {
                    userScrolling = true
                    pause()
                } else if phase == .idle, userScrolling {
                    userScrolling = false
                    let geometry = context.geometry
                    if Self.bottomOffset(geometry) - geometry.contentOffset.y <= bottomTolerance { resume() }
                }
            }
    }

    nonisolated private static func bottomOffset(_ geometry: ScrollGeometry) -> CGFloat {
        max(-geometry.contentInsets.top,
            geometry.contentSize.height + geometry.contentInsets.bottom - geometry.containerSize.height)
    }

    private func follow(_ offset: CGFloat) {
        guard followTarget != nil, !userScrolling else { return }
        var transaction = Transaction(animation: nil)
        transaction.disablesAnimations = true
        withTransaction(transaction) { position.scrollTo(y: offset) }
    }
}

private struct ChatBottomEdge: PreferenceKey {
    enum Target: Hashable { case bottom }
    static let target = Target.bottom
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() }
}
