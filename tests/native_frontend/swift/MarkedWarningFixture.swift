import Combine
import SwiftUI
import UIKit

// Native facade stand-in only: the production TheatrePlayback admission,
// warning view, source presenter, menu, and transaction execute unchanged.
@MainActor final class SSNPlayback {
    let view = UIView()
    var qualities: [String] = []
    var preferredQuality = "auto"
    var effectiveQuality: String { qualities.contains(preferredQuality) ? preferredQuality : "auto" }
    var phase = 0, errorCode = 0
    var isPaused = false, isMuted: Bool
    private(set) var startCount = 0
    private(set) var theatre = false
    init(channel: String, preview: Bool = false) { isMuted = preview; theatre = !preview }
    func start() { startCount += 1; phase = 3 }
    func stop() { phase = 0 }
    func enterTheatre() -> Bool { theatre = true; return true }
}

@MainActor private final class MarkedWarningFixtureState: ObservableObject {
    @Published var warnings = true
    @Published var thumbnails = false
    @Published var closed = false
    @Published var showingTheatre: Bool
    let playback: TheatrePlayback
    private var configured = false
    init() {
        let theatre = !ProcessInfo.processInfo.arguments.contains("--marked-preview")
        showingTheatre = theatre
        playback = TheatrePlayback(channel: "fixture", preview: !theatre)
        thumbnails = ProcessInfo.processInfo.arguments.contains("--marked-thumbnails-enabled")
    }
    func configure(close: @escaping () -> Void) {
        playback.bindContentOwner(valid: { true }, close: close)
        guard !configured else { return }; configured = true
        playback.configureContentGate { [weak self] completion in
            MarkedContentGate(load: { ["Fixture content label", "Second fixture label"] }, valid: { true },
                saveWarnings: { self?.warnings = $0 }, saveThumbnails: { self?.thumbnails = $0 }, thumbnailsEnabled: { self?.thumbnails == true }, completion: completion)
        }
    }
    func beginTheatre() {
        configure(close: { [weak self] in self?.closed = true })
        playback.startIfNeeded()
    }
    func session(source: UIView) -> ContextPreviewSession {
        weak var transaction: ContextPreviewSession?
        configure(close: { transaction?.cancel() })
        let width: CGFloat = 360
        let content = UIHostingController(rootView: MarkedWarningFixtureSlot(state: self, playback: playback))
        let controller = QuickLookController(content: content, size: CGSize(width: width, height: width * 9 / 16 + 160))
        let session = ContextPreviewSession(controller: controller, claim: { _ in true }, release: { _ in }, valid: { true },
            start: playback.start, stop: { [weak self] in self?.playback.stop(); self?.closed = true }, handoff: { [weak self] in
                guard let self else { return false }
                self.playback.bindContentOwner(valid: { true }, close: { [weak self] in self?.closed = true })
                self.playback.enterTheatre(); self.showingTheatre = true; return true
            })
        session.videoTapAvailability = playback.$contentGate.map { $0 == nil }.eraseToAnyPublisher()
        transaction = session; return session
    }
}

private struct MarkedVideoBounds: UIViewRepresentable {
    func makeUIView(context: Context) -> UIView {
        let view = UIView(); view.isUserInteractionEnabled = false
        view.isAccessibilityElement = true; view.accessibilityIdentifier = "marked.video-slot"
        view.accessibilityLabel = "Video area"; return view
    }
    func updateUIView(_ view: UIView, context: Context) {}
}

private struct MarkedWarningFixtureSlot: View {
    @ObservedObject var state: MarkedWarningFixtureState
    @ObservedObject var playback: TheatrePlayback
    private var video: some View {
        Group {
            if let gate = playback.contentGate { MarkedContentWarning(gate: gate) }
            else { Color.purple.overlay { Text("Admitted") } }
        }
    }
    var body: some View {
        VStack(spacing: 0) {
            // Match the production theatre's externally sized video canvas.
            Color.black.aspectRatio(16.0 / 9.0, contentMode: .fit)
                .overlay { video }
                .background { MarkedVideoBounds() }
            Text("Fixture channel identity and stream details remain visible").padding(12)
            Text(verbatim: "warnings=\(state.warnings) thumbnails=\(state.thumbnails)")
                .accessibilityIdentifier("marked.preferences")
            Text(verbatim: "starts=\(playback.native!.startCount)")
                .accessibilityIdentifier("marked.media-starts")
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(Color(uiColor: .secondarySystemBackground))
    }
}

struct MarkedWarningFixture: View {
    @StateObject private var state = MarkedWarningFixtureState()
    var body: some View {
        VStack {
            if state.closed {
                Text("Closed")
                Text(verbatim: "warnings=\(state.warnings) thumbnails=\(state.thumbnails)")
                    .accessibilityIdentifier("marked.preferences")
                Text(verbatim: "starts=\(state.playback.native!.startCount)")
                    .accessibilityIdentifier("marked.media-starts")
            }
            else if state.showingTheatre {
                MarkedWarningFixtureSlot(state: state, playback: state.playback)
                    .onAppear { state.beginTheatre() }
                Text("Theatre").accessibilityIdentifier("marked.destination")
            } else {
                ThumbnailActions(label: "Marked stream thumbnail", open: { state.showingTheatre = true },
                    preview: { state.session(source: $0) })
                    .frame(width: 140, height: 140 * 9 / 16)
                    .background(.gray).padding(.top, 200)
                Text("Feed remains underneath")
            }
            Spacer()
        }.frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
