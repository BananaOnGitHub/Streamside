// Donor-free integration fixture. A locally encoded movie exercises a real
// AVPlayerLayer through the production passive surface and anchored preview.
import SwiftUI
import UIKit
import AVFoundation
import CoreVideo

private enum FixtureMovie {
    static func create() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("context-video.mov")
        try? FileManager.default.removeItem(at: url)
        let writer = try AVAssetWriter(outputURL: url, fileType: .mov)
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: 320, AVVideoHeightKey: 180])
        let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
            kCVPixelBufferWidthKey as String: 320, kCVPixelBufferHeightKey as String: 180])
        guard writer.canAdd(input) else { throw NSError(domain: "FixtureMovie", code: 1) }
        writer.add(input)
        guard writer.startWriting() else { throw writer.error ?? NSError(domain: "FixtureMovie", code: 2) }
        writer.startSession(atSourceTime: .zero)
        let deadline = Date().addingTimeInterval(12)
        for frame in 0..<90 {
            while !input.isReadyForMoreMediaData && writer.status == .writing && Date() < deadline { Thread.sleep(forTimeInterval: 0.002) }
            guard input.isReadyForMoreMediaData, writer.status == .writing, Date() < deadline,
                  let pool = adaptor.pixelBufferPool else { throw writer.error ?? NSError(domain: "FixtureMovie", code: 3) }
            var buffer: CVPixelBuffer?
            guard CVPixelBufferPoolCreatePixelBuffer(nil, pool, &buffer) == kCVReturnSuccess, let buffer else {
                throw NSError(domain: "FixtureMovie", code: 4)
            }
            CVPixelBufferLockBaseAddress(buffer, [])
            if let base = CVPixelBufferGetBaseAddress(buffer) {
                let stride = CVPixelBufferGetBytesPerRow(buffer)
                for y in 0..<180 {
                    let row = base.advanced(by: y * stride).assumingMemoryBound(to: UInt8.self)
                    for x in 0..<320 {
                        // Alternating red/blue seconds: screenshot checks must
                        // observe both, not merely a readyForDisplay flag.
                        row[x * 4] = (frame / 15).isMultiple(of: 2) ? 0 : 240
                        row[x * 4 + 1] = 0
                        row[x * 4 + 2] = (frame / 15).isMultiple(of: 2) ? 240 : 0
                        row[x * 4 + 3] = 255
                    }
                }
            }
            CVPixelBufferUnlockBaseAddress(buffer, [])
            guard adaptor.append(buffer, withPresentationTime: CMTime(value: Int64(frame), timescale: 15)) else {
                throw writer.error ?? NSError(domain: "FixtureMovie", code: 5)
            }
        }
        input.markAsFinished()
        let finished = DispatchSemaphore(value: 0)
        writer.finishWriting { finished.signal() }
        guard finished.wait(timeout: .now() + 12) == .success, writer.status == .completed else {
            throw writer.error ?? NSError(domain: "FixtureMovie", code: 6)
        }
        return url
    }
}

private final class FixtureVideo: UIView {
    override class var layerClass: AnyClass { AVPlayerLayer.self }
    var videoLayer: AVPlayerLayer { layer as! AVPlayerLayer }
}

// Observe the actual UIKit presentation tree, not a synthetic animation model.
// Bounded to this owned fixture; no snapshots of account or donor content.
@MainActor private final class PreviewMotionProbe: NSObject {
    private var link: CADisplayLink?
    private var frames = 0
    private var source = CGRect.zero
    private var finalWidth: CGFloat = 0
    private(set) var intermediate = false
    func begin(source: UIView, finalWidth: CGFloat) {
        guard let window = source.window else { return }
        begin(source: source.convert(source.bounds, to: window), finalWidth: finalWidth)
    }
    func begin(source: CGRect, finalWidth: CGFloat) {
        finish(); frames = 0; intermediate = false
        self.source = source; self.finalWidth = finalWidth
        link = CADisplayLink(target: self, selector: #selector(sample))
        link?.add(to: .main, forMode: .common)
    }
    @objc private func sample() {
        guard frames < 600, !intermediate else { finish(); return }
        frames += 1
        // UIKit may animate a separate snapshot, rather than the supplied
        // controller's layer. Inspect public presentation layers in the scene,
        // bounded by count, and require an animated intermediate rectangle
        // that contains the actual source center on its way to preview width.
        let point = CGPoint(x: source.midX, y: source.midY)
        for scene in UIApplication.shared.connectedScenes {
            guard let scene = scene as? UIWindowScene else { continue }
            for window in scene.windows where !window.isHidden {
                var pending = [window.layer], examined = 0
                while let layer = pending.popLast(), examined < 3000 {
                    examined += 1
                    pending.append(contentsOf: layer.sublayers ?? [])
                    guard let shown = layer.presentation() else { continue }
                    let rect = shown.convert(shown.bounds, to: nil)
                    var visibleAlpha: Float = 1
                    var visibleAncestor: CALayer? = shown
                    while let current = visibleAncestor { visibleAlpha *= current.opacity; visibleAncestor = current.superlayer }
                    guard visibleAlpha > 0.05, rect.width > source.width + 5, rect.width < finalWidth - 5,
                          rect.height >= source.height * 0.8,
                          rect.insetBy(dx: -5, dy: -5).contains(point) else { continue }
                    var ancestor: CALayer? = layer
                    while let current = ancestor {
                        if !(current.animationKeys() ?? []).isEmpty { intermediate = true; break }
                        ancestor = current.superlayer
                    }
                    if intermediate { return }
                }
            }
        }
    }
    func finish() { link?.invalidate(); link = nil }
}

@MainActor final class ContextPreviewFixture: ObservableObject {
    @Published var ready = "Preparing video"
    @Published var previews = 0
    @Published var watches = 0
    @Published var stops = 0
    @Published var creations = 0
    @Published var targetResult = "Not checked"
    @Published var motionResult = "Not checked"
    private var movie: URL?
    private var valid = true
    private var sourceCenter: CGPoint?
    private var highlighted = false
    private var player: AVQueuePlayer?
    private var looper: AVPlayerLooper?
    private var surface: FixtureVideo?
    private var motion: PreviewMotionProbe?
    private var entryAnimated = false
    private var previewWidth: CGFloat = 0
    private let long = ProcessInfo.processInfo.arguments.contains("--long-panel")
    let image = UIGraphicsImageRenderer(size: CGSize(width: 160, height: 90)).image { context in
        UIColor.systemIndigo.setFill(); context.fill(CGRect(x: 0, y: 0, width: 160, height: 90))
        UIImage(systemName: "play.fill")?.withTintColor(.white, renderingMode: .alwaysOriginal)
            .draw(in: CGRect(x: 65, y: 30, width: 30, height: 30))
    }
    func prepare() async {
        do {
            movie = try await Task.detached { try FixtureMovie.create() }.value
            ready = "Video ready"
        } catch { ready = "Video failed: \(error)" }
    }
    func target(dismissing: Bool, source: CGRect, center: CGPoint) {
        let aligned = abs(source.midX - center.x) < 0.5 && abs(source.midY - center.y) < 0.5
        if !dismissing { sourceCenter = center; highlighted = aligned }
        else {
            entryAnimated = motion?.intermediate == true
            motion?.begin(source: source, finalWidth: previewWidth)
            let same = sourceCenter.map { hypot($0.x - center.x, $0.y - center.y) < 1 } ?? false
            targetResult = aligned && highlighted && same ? "Returned to source" : "Invalid source target"
        }
    }
    func directWatch() { watches += 1 }
    private func stop() {
        stops += 1; player?.pause(); player?.removeAllItems()
        surface?.videoLayer.player = nil
        looper = nil; player = nil; surface = nil
        motion?.finish(); motionResult = entryAnimated && motion?.intermediate == true ? "Animated source" : "No observed animation"
    }
    func preview(_ source: UIView) -> ContextPreviewSession? {
        guard let movie, player == nil else { return nil }
        valid = true
        let player = AVQueuePlayer(); player.isMuted = true
        let surface = FixtureVideo(); surface.videoLayer.player = player; surface.videoLayer.videoGravity = .resizeAspect
        self.player = player; self.surface = surface
        looper = AVPlayerLooper(player: player, templateItem: AVPlayerItem(url: movie)); creations += 1
        let width = min(380, (source.window?.bounds.width ?? 390) - 32)
        previewWidth = width; entryAnimated = false
        let detailsHeight: CGFloat = long ? 220 : 150
        let content = UIHostingController(rootView: QuickLookPanel(width: width, detailsHeight: detailsHeight) {
            PassivePlayerSurface(surface: surface, topCornerRadius: 24)
                .accessibilityElement().accessibilityLabel("Decoded fixture video")
                .accessibilityIdentifier("fixture.preview-video")
        } details: {
            VStack(alignment: .leading, spacing: 10) {
                Label("Fixture channel", systemImage: "person.crop.circle.fill").font(.headline)
                Text(self.long ? String(repeating: "Full stream title 👋 ", count: 30) : "Full stream title")
                Text("Category")
                AllStreamTags(tags: self.long ? (0..<20).map { "Tag\($0)" } : ["English", "Music"])
                Text("Final preview detail").accessibilityIdentifier("preview-last-detail")
            }
        })
        let controller = QuickLookController(content: content, size: CGSize(width: width, height: width * 9 / 16 + detailsHeight))
        let probe = PreviewMotionProbe(); motion = probe; probe.begin(source: source, finalWidth: width)
        let session = ContextPreviewSession(controller: controller, claim: { _ in true }, release: { _ in }, valid: { self.valid }, start: {
            self.previews += 1; player.play()
            if ProcessInfo.processInfo.arguments.contains("--cancel-preview") {
                DispatchQueue.main.asyncAfter(deadline: .now() + 6) {
                    self.valid = false
                    NotificationCenter.default.post(name: Notification.Name("SSNNativeServiceDidChange"), object: nil)
                }
            }
        }, stop: { self.stop() }, handoff: {
            guard self.valid, let root = source.window?.rootViewController, root.presentedViewController == nil else { return false }
            self.watches += 1
            probe.finish(); self.motionResult = probe.intermediate ? "Animated source" : "No observed animation"
            let theatre = UIHostingController(rootView: VStack {
                PassivePlayerSurface(surface: surface).frame(height: width * 9 / 16)
                    .accessibilityElement().accessibilityLabel("Transferred fixture video").accessibilityIdentifier("fixture.theatre-video")
                Text("Same player: \(self.creations)").accessibilityIdentifier("preview-watched")
                Button("Close fixture theatre") { root.dismiss(animated: true) { self.stop() } }
            })
            theatre.modalPresentationStyle = .fullScreen; theatre.modalTransitionStyle = .crossDissolve
            root.present(theatre, animated: true) { player.isMuted = false }
            return true
        })
        return session
    }
}

struct ContextPreviewFixtureView: View {
    @StateObject private var fixture = ContextPreviewFixture()
    var body: some View {
        VStack {
            Group {
                Text(fixture.ready).accessibilityIdentifier("fixture-ready")
                Text("Watches: \(fixture.watches)").accessibilityIdentifier("thumbnail-watches")
                Text("Previews: \(fixture.previews)").accessibilityIdentifier("thumbnail-previews")
                Text("Stops: \(fixture.stops)").accessibilityIdentifier("preview-stops")
                Text(fixture.targetResult).accessibilityIdentifier("source-target")
                Text(fixture.motionResult).accessibilityIdentifier("source-motion")
            }.font(.caption).frame(height: 17)
            ScrollView {
                VStack(spacing: 24) {
                    ThumbnailActions(image: fixture.image, label: "Stream thumbnail", open: fixture.directWatch,
                                     preview: fixture.preview, observeTarget: fixture.target)
                        .frame(width: 160, height: 90).accessibilityIdentifier("preview-thumbnail")
                        .padding(.top, 40)
                    ForEach(0..<30) { Text("Scroll row \($0)").frame(height: 50) }
                }.frame(maxWidth: .infinity)
            }
        }.task { await fixture.prepare() }
    }
}
