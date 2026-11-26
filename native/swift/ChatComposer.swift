import SwiftUI
import UIKit

enum ChatDelivery {
    case sent, rejected, unconfirmed
}

@MainActor
struct ChatComposer: View {
    let available: Bool
    let send: @MainActor (String) async -> ChatDelivery
    @State private var draft = ""
    @State private var feedback: String?
    @State private var sending: Task<Void, Never>?
    @FocusState private var focused: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    private var message: String {
        draft.trimmingCharacters(in: .whitespacesAndNewlines)
            .components(separatedBy: .newlines).joined(separator: " ")
    }

    var body: some View {
        let text = message
        let tooLong = text.utf16.count > 500
        VStack(alignment: .leading, spacing: 4) {
            if let note = tooLong ? "Messages can be up to 500 characters." : feedback {
                Text(note).font(.caption).foregroundStyle(.secondary)
                    .accessibilityIdentifier("chat.send-status")
            }
            if #available(iOS 26.0, *), !reduceTransparency {
                GlassEffectContainer(spacing: 6) {
                    controls(text: text, tooLong: tooLong)
                }
            } else {
                controls(text: text, tooLong: tooLong)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 6)
        .onChange(of: draft) { _ in if sending == nil { feedback = nil } }
        .onChange(of: available) { enabled in
            if !enabled {
                focused = false
                cancelSend()
            }
        }
        .onDisappear { cancelSend() }
    }

    private func controls(text: String, tooLong: Bool) -> some View {
        HStack(spacing: 8) {
            TextField(available ? "Send a message" : "Chat is unavailable", text: $draft)
                .focused($focused)
                .textFieldStyle(.plain)
                .submitLabel(.send)
                .onSubmit { submit() }
                .padding(.horizontal, 16)
                .frame(minHeight: 44)
                .disabled(!available)
                .accessibilityIdentifier("chat.message-input")
                .modifier(ChatComposerSurface(shape: Capsule(), interactive: false))

            if !text.isEmpty {
                Button(action: submit) {
                    Group {
                        if sending != nil { ProgressView() }
                        else { Image(systemName: "arrow.up").font(.body.weight(.semibold)) }
                    }
                    .frame(width: 44, height: 44)
                    .contentShape(.interaction, Circle())
                    .modifier(ChatComposerSurface(shape: Circle(), interactive: true))
                }
                .buttonStyle(.plain)
                .contentShape(.interaction, Circle())
                .disabled(!available || tooLong || sending != nil)
                .accessibilityLabel("Send message")
                .accessibilityIdentifier("chat.send")
                .transition(reduceMotion ? .opacity : .offset(x: 58).combined(with: .opacity))
            }
        }
        .animation(.easeOut(duration: reduceMotion ? 0.16 : 0.25), value: text.isEmpty)
    }

    private func submit() {
        let text = message
        guard available, sending == nil, !text.isEmpty, text.utf16.count <= 500 else { return }
        feedback = nil
        let submittedDraft = draft
        sending = Task {
            let result = await send(text)
            guard !Task.isCancelled else { return }
            sending = nil
            switch result {
            case .sent:
                if draft == submittedDraft { draft = "" }
            case .rejected:
                feedback = "Twitch didn’t accept this message."
            case .unconfirmed:
                feedback = "Delivery couldn’t be confirmed."
            }
        }
    }

    private func cancelSend() {
        guard let sending else { return }
        sending.cancel()
        self.sending = nil
        feedback = "Delivery couldn’t be confirmed."
    }
}

private struct ChatComposerSurface<Outline: Shape>: ViewModifier {
    let shape: Outline
    let interactive: Bool
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    func body(content: Content) -> some View {
        if reduceTransparency {
            content.background(Color(uiColor: .secondarySystemBackground), in: shape)
        } else if #available(iOS 26.0, *) {
            content.glassEffect(.regular.interactive(interactive), in: shape)
        } else {
            content.background(.regularMaterial, in: shape)
        }
    }
}
