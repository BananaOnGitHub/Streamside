import SwiftUI

// Replaces only the video slot. Channel information and contextual actions stay
// in their existing preview/theatre hierarchy; no window-covering consent modal.
struct MarkedContentWarning: View {
    @ObservedObject var gate: MarkedContentGate
    var body: some View {
        VStack(spacing: 5) {
            ScrollView {
                VStack(spacing: 4) {
                    Image(systemName: "eye.slash").font(.body).accessibilityHidden(true)
                    switch gate.stage {
                    case .loading: ProgressView("Loading stream content labels…")
                    case .warning:
                        Text("This stream has been marked as containing:").fontWeight(.semibold)
                        Text(gate.labels.joined(separator: ", ")).foregroundStyle(.secondary)
                        Text("Do you want to continue?")
                    case .thumbnails:
                        Text("Show thumbnails for marked streams?").fontWeight(.semibold)
                        Text("You can change this in Followed streams settings.").foregroundStyle(.secondary)
                    case .failed:
                        Text("Couldn’t load Twitch’s content labels.").fontWeight(.semibold)
                        Text("Check your connection and try again.").foregroundStyle(.secondary)
                    case .finished: EmptyView()
                    }
                }.frame(maxWidth: .infinity)
            }.scrollBounceBehavior(.basedOnSize)
            switch gate.stage {
            case .warning:
                Button { gate.dontShowAgain.toggle() } label: {
                    Label("Don’t show again", systemImage: gate.dontShowAgain ? "checkmark.square.fill" : "square")
                }
                .accessibilityIdentifier("marked.dontShowAgain")
                .accessibilityValue(gate.dontShowAgain ? "Selected" : "Not selected")
                .accessibilityAddTraits(gate.dontShowAgain ? .isSelected : [])
                .modifier(ContentWarningButton(prominent: false)).controlSize(.mini)
                HStack(spacing: 10) {
                    closeButton
                    Button("Continue") { gate.proceed() }.modifier(ContentWarningButton(prominent: true))
                }
            case .thumbnails:
                HStack(spacing: 8) {
                    Button("Keep hidden") { gate.chooseThumbnails(false) }.modifier(ContentWarningButton(prominent: false))
                    Button("Show thumbnails") { gate.chooseThumbnails(true) }.modifier(ContentWarningButton(prominent: true))
                }
                closeButton
            case .failed:
                HStack(spacing: 10) {
                    closeButton
                    Button("Try again") { gate.start() }.modifier(ContentWarningButton(prominent: true))
                }
            case .loading: closeButton
            case .finished: EmptyView()
            }
        }
        .controlSize(.small).font(.caption).multilineTextAlignment(.center)
        .padding(8).frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(.black).environment(\.colorScheme, .dark)
    }
    private var closeButton: some View {
        Button("Close", role: .cancel) { gate.close() }.modifier(ContentWarningButton(prominent: false))
    }
}

private struct ContentWarningButton: ViewModifier {
    let prominent: Bool
    @AppStorage(PlayerPreferences.glassButtonsKey) private var glass = true
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @ViewBuilder func body(content: Content) -> some View {
        if glass && !reduceTransparency {
            if #available(iOS 26.0, *) {
                if prominent { content.buttonStyle(.glassProminent) }
                else { content.buttonStyle(.glass) }
            } else { fallback(content) }
        } else { fallback(content) }
    }
    @ViewBuilder private func fallback(_ content: Content) -> some View {
        if prominent { content.buttonStyle(.borderedProminent) }
        else { content.buttonStyle(.bordered) }
    }
}
