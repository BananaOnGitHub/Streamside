import SwiftUI

struct TheatreChat: View {
    let channel: String?
    @State private var status: TwitchGuestChat.Status = .connecting
    @State private var transcript = TwitchChatTranscript()
    @State private var connectionID = UUID()

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Stream chat").font(.footnote.weight(.semibold))
                Spacer()
                if !transcript.messages.isEmpty, status != .listening {
                    Text(statusText).font(.caption).foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)

            if transcript.messages.isEmpty {
                Text(statusText).font(.footnote).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollViewReader { reader in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 5) {
                            ForEach(transcript.messages) { message in
                                row(message).id(message.id)
                            }
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 4)
                    }
                    .onAppear { scroll(reader, to: transcript.messages.last?.id) }
                    .onChange(of: transcript.messages.last?.id) { scroll(reader, to: $0) }
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .task(id: channel) {
            let id = UUID()
            connectionID = id
            guard let channel else { return }
            await TwitchGuestChat.listen(channel: channel) { update in
                guard connectionID == id, !Task.isCancelled else { return }
                switch update {
                case .status(let next): if next != status { status = next }
                case .events(let events):
                    var transaction = Transaction(animation: nil)
                    transaction.disablesAnimations = true
                    withTransaction(transaction) { transcript.apply(events) }
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

    private func scroll(_ reader: ScrollViewProxy, to id: String?) {
        guard let id else { return }
        var transaction = Transaction(animation: nil)
        transaction.disablesAnimations = true
        withTransaction(transaction) { reader.scrollTo(id, anchor: .bottom) }
    }
}
