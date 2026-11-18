import SwiftUI
import UIKit

struct MarkedContentWarning: View {
    @ObservedObject var gate: MarkedContentGate
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    var body: some View {
        ZStack {
            Color.black.opacity(0.42).ignoresSafeArea()
            VStack(spacing: 18) {
                Image(systemName: "eye.slash").font(.largeTitle).accessibilityHidden(true)
                switch gate.stage {
                case .loading:
                    ProgressView("Loading stream content labels…")
                    Button("Close", role: .cancel) { gate.close() }
                case .warning:
                    Text("This stream has been marked as containing:").font(.headline)
                    ScrollView {
                        VStack(spacing: 8) { ForEach(Array(gate.labels.enumerated()), id: \.offset) { _, label in Text(label) } }
                            .frame(maxWidth: .infinity)
                    }.frame(maxHeight: 150).fixedSize(horizontal: false, vertical: true)
                    Text("Do you want to continue?")
                    Toggle(isOn: $gate.dontShowAgain) {
                        Label("Don’t show again", systemImage: gate.dontShowAgain ? "checkmark.square.fill" : "square")
                    }
                    .toggleStyle(.button).accessibilityIdentifier("marked.dontShowAgain")
                    HStack(spacing: 24) {
                        Button("Close", role: .cancel) { gate.close() }
                        Button("Continue") { gate.proceed() }.buttonStyle(.borderedProminent)
                    }
                case .thumbnails:
                    Text("Show thumbnails for marked streams?").font(.headline)
                    Text("You can change this in Followed streams settings.").font(.subheadline)
                    HStack(spacing: 24) {
                        Button("Keep hidden") { gate.chooseThumbnails(false) }
                        Button("Show thumbnails") { gate.chooseThumbnails(true) }.buttonStyle(.borderedProminent)
                    }
                case .failed:
                    Text("Couldn’t load Twitch’s content labels.").font(.headline)
                    Text("Check your connection and try again.").font(.subheadline)
                    HStack(spacing: 24) {
                        Button("Close", role: .cancel) { gate.close() }
                        Button("Try again") { gate.start() }
                    }
                case .finished: EmptyView()
                }
            }
            .multilineTextAlignment(.center)
            .padding(24).frame(maxWidth: 360)
            .background {
                if reduceTransparency { RoundedRectangle(cornerRadius: 24).fill(Color(uiColor: .systemBackground)) }
                else { RoundedRectangle(cornerRadius: 24, style: .continuous).fill(.regularMaterial) }
            }
            .padding(20).accessibilityIdentifier("marked.warning")
        }
        .task { gate.start() }
    }
}
