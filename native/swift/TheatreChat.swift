import SwiftUI
import UIKit

struct TheatreChat: View {
    let channel: String?
    @State private var status: TwitchGuestChat.Status = .connecting
    @State private var timeline = TwitchChatTimeline()
    @State private var connectionID = UUID()

    var body: some View {
        StreamChatTranscript(timeline: $timeline, statusText: statusText, listening: status == .listening)
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
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @State private var userScrolling = false
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
                ScrollViewReader { reader in
                    trackedScroll(reader)
                        .onAppear { scrollToBottom(reader) }
                        .onChange(of: followTarget) { id in
                            if id != nil { scrollToBottom(reader) }
                        }
                        .overlay(alignment: .bottom) { catchUpPill }
                        .clipped()
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    @ViewBuilder private func trackedScroll(_ reader: ScrollViewProxy) -> some View {
        if #available(iOS 18.0, *) {
            transcriptScroll(measureBottom: false)
                .defaultScrollAnchor(timeline.isPaused ? nil : .bottom, for: .sizeChanges)
                .onScrollPhaseChange { _, phase, context in
                    if phase == .interacting {
                        userScrolling = true
                        timeline.pause()
                    } else if phase == .idle, userScrolling {
                        userScrolling = false
                        if context.geometry.contentSize.height - context.geometry.visibleRect.maxY <= bottomTolerance {
                            timeline.resume()
                        }
                    }
                }
        } else {
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
                    .onChange(of: viewport.size.height) { _ in
                        if !timeline.isPaused { scrollToBottom(reader) }
                    }
            }
        }
    }

    private func transcriptScroll(measureBottom: Bool) -> some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 5) {
                ForEach(timeline.messages) { message in
                    VStack(alignment: .leading, spacing: 5) {
                        if message.id == timeline.firstNewMessageID { unreadMarker }
                        row(message)
                    }
                    .id(message.id)
                }
            }
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
        return Text("\(author): \(Text(verbatim: message.body))")
            .font(.subheadline)
            .frame(maxWidth: .infinity, alignment: .leading)
            .fixedSize(horizontal: false, vertical: true)
    }

    private func scrollToBottom(_ reader: ScrollViewProxy) {
        guard let id = timeline.messages.last?.id else { return }
        var transaction = Transaction(animation: nil)
        transaction.disablesAnimations = true
        withTransaction(transaction) { reader.scrollTo(id, anchor: .bottom) }
    }
}

private struct ChatBottomEdge: PreferenceKey {
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() }
}
