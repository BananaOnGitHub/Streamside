import SwiftUI
import UIKit
import ImageIO

private final class ChatArtworkRedirect: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(request.url.map(ChatArtworkRequest.allowed) == true ? request : nil)
    }
}

struct ChatArtwork: @unchecked Sendable {
    let image: UIImage
    let first: UIImage
    let cost: Int
}

actor ChatArtworkLoader {
    private let session: URLSession
    init() {
        let config = URLSessionConfiguration.ephemeral
        config.httpShouldSetCookies = false
        config.httpCookieStorage = nil
        config.urlCredentialStorage = nil
        config.httpMaximumConnectionsPerHost = 2
        config.timeoutIntervalForRequest = 5
        config.timeoutIntervalForResource = 8
        config.urlCache = nil
        session = URLSession(configuration: config, delegate: ChatArtworkRedirect(), delegateQueue: nil)
    }
    func load(_ request: ChatArtworkRequest) async -> ChatArtwork? {
        for url in [request.animated, request.still].compactMap({ $0 }) {
            guard !Task.isCancelled, ChatArtworkRequest.allowed(url) else { return nil }
            do {
                let (data, response) = try await session.data(from: url)
                guard !Task.isCancelled, let http = response as? HTTPURLResponse, http.statusCode == 200,
                      http.url.map(ChatArtworkRequest.allowed) == true,
                      http.mimeType?.hasPrefix("image/") == true, data.count <= 1_500_000 else { continue }
                if let art = Self.decode(data) { return art }
            } catch { if Task.isCancelled { return nil } }
        }
        return nil
    }
    // Frames are downsampled, not forced into a square. Limit decoded memory
    // even for malformed/oversized GIFs and retain the first frame for Reduce Motion.
    static func decode(_ data: Data) -> ChatArtwork? {
        guard data.count <= 1_500_000, let source = CGImageSourceCreateWithData(data as CFData, nil),
              CGImageSourceGetCount(source) > 0 else { return nil }
        let count = CGImageSourceGetCount(source)
        let options: [CFString: Any] = [kCGImageSourceCreateThumbnailFromImageAlways: true,
                                        kCGImageSourceThumbnailMaxPixelSize: 84,
                                        kCGImageSourceCreateThumbnailWithTransform: true,
                                        kCGImageSourceShouldCacheImmediately: true]
        var frames: [UIImage] = [], duration = 0.0, cost = 0
        let step = max(1, (count + 47) / 48)
        for index in stride(from: 0, to: count, by: step).prefix(48) {
            guard let cg = CGImageSourceCreateThumbnailAtIndex(source, index, options as CFDictionary) else { continue }
            let properties = CGImageSourceCopyPropertiesAtIndex(source, index, nil) as? [CFString: Any]
            let gif = properties?[kCGImagePropertyGIFDictionary] as? [CFString: Any]
            let rawDelay = gif?[kCGImagePropertyGIFUnclampedDelayTime] as? Double ?? gif?[kCGImagePropertyGIFDelayTime] as? Double ?? 0.1
            duration += min(1, max(0.02, rawDelay.isFinite ? rawDelay : 0.1)) * Double(step)
            cost += cg.bytesPerRow * cg.height
            frames.append(UIImage(cgImage: cg))
        }
        guard let first = frames.first, cost <= 2_000_000 else { return nil }
        let image = frames.count > 1 ? UIImage.animatedImage(with: frames, duration: duration) ?? first : first
        return ChatArtwork(image: image, first: first, cost: cost)
    }
}

@MainActor
final class ChatArtworkStore: ObservableObject {
    @Published private(set) var images: [ChatArtworkRequest: ChatArtwork] = [:]
    private let loader = ChatArtworkLoader()
    private var wanted: [ChatArtworkRequest] = []
    private var attempted: [ChatArtworkRequest: TimeInterval] = [:]
    private var order: [ChatArtworkRequest] = []
    private var worker: Task<Void, Never>?
    private var active = false
    func setActive(_ value: Bool) {
        active = value
        if value { startIfNeeded() }
        else { worker?.cancel(); wanted = [] }
    }
    func update(_ requests: [ChatArtworkRequest]) {
        var seen = Set<ChatArtworkRequest>()
        wanted = Array(requests.filter { seen.insert($0).inserted }.prefix(48))
        startIfNeeded()
    }
    private func next() -> ChatArtworkRequest? {
        let now = ProcessInfo.processInfo.systemUptime
        return wanted.first { images[$0] == nil && attempted[$0].map { now - $0 >= 90 } != false }
    }
    private func startIfNeeded() {
        guard active, worker == nil, next() != nil else { return }
        worker = Task {
            while active, !Task.isCancelled, let key = next() {
                let art = await loader.load(key)
                guard active, !Task.isCancelled else { break }
                attempted[key] = ProcessInfo.processInfo.systemUptime
                order.removeAll { $0 == key }; order.append(key)
                if let art { images[key] = art; SSNChatArtEvent(art.image.images == nil ? 4 : 5) }
                else { SSNChatArtEvent(6) }
                while order.count > 96 || images.values.reduce(0, { $0 + $1.cost }) > 12 * 1024 * 1024 {
                    let evicted = order.removeFirst()
                    images.removeValue(forKey: evicted)
                    // Keep a short suppression for a visible but evicted asset.
                    if !wanted.contains(evicted) { attempted.removeValue(forKey: evicted) }
                }
                if attempted.count > 192 { attempted = attempted.filter { order.contains($0.key) || wanted.contains($0.key) } }
            }
            worker = nil
            if Task.isCancelled { startIfNeeded() }
        }
    }
}

struct ChatAnimatedArtwork: UIViewRepresentable {
    let artwork: ChatArtwork
    let animate: Bool
    func makeUIView(context: Context) -> UIImageView {
        let view = UIImageView()
        view.contentMode = .scaleAspectFit
        view.clipsToBounds = true
        return view
    }
    func updateUIView(_ view: UIImageView, context: Context) {
        let image = animate ? artwork.image : artwork.first
        if view.image !== image { view.image = image }
    }
    static func dismantleUIView(_ view: UIImageView, coordinator: ()) {
        view.stopAnimating(); view.image = nil
    }
}

// A flowing inline layout keeps emotes and their surrounding words in the
// same paragraph, without imposing square artwork or fixed-width characters.
struct ChatInlineLayout: Layout {
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        arrange(width: proposal.width ?? 300, subviews: subviews).size
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let layout = arrange(width: bounds.width, subviews: subviews)
        for (index, rect) in layout.rects.enumerated() {
            subviews[index].place(at: CGPoint(x: bounds.minX + rect.minX, y: bounds.minY + rect.minY),
                                  anchor: .topLeading, proposal: ProposedViewSize(rect.size))
        }
    }
    private func arrange(width: CGFloat, subviews: Subviews) -> (size: CGSize, rects: [CGRect]) {
        let limit = max(1, width)
        var rects: [CGRect] = [], x: CGFloat = 0, y: CGFloat = 0, height: CGFloat = 0, start = 0
        func finish() {
            for index in start..<rects.count { rects[index].origin.y = y + (height - rects[index].height) / 2 }
            y += height
            start = rects.count; x = 0; height = 0
        }
        for view in subviews {
            var size = view.sizeThatFits(.unspecified)
            if size.width > limit { size = view.sizeThatFits(ProposedViewSize(width: limit, height: nil)) }
            if x > 0 && x + size.width > limit { finish(); y += 2 }
            rects.append(CGRect(x: x, y: y, width: min(limit, size.width), height: size.height))
            x += size.width; height = max(height, size.height)
        }
        finish()
        return (CGSize(width: limit, height: y), rects)
    }
}

struct ChatRichRow: View {
    let author: String
    let authorColor: Color
    let parts: [ChatRichText.Part]
    let images: [ChatArtworkRequest: ChatArtwork]
    let animate: Bool
    @ScaledMetric(relativeTo: .subheadline) private var iconHeight: CGFloat = 23
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        ChatInlineLayout {
            Text(verbatim: author + ": ").bold().foregroundColor(authorColor)
            ForEach(parts.indices, id: \.self) { index in
                switch parts[index] {
                case .text(let text):
                    let words = ChatRichText.words(text)
                    ForEach(words.indices, id: \.self) { index in
                        Text(verbatim: words[index])
                    }
                case .emote(let original, let art):
                    icon(art, original: original)
                case .cheer(let original, let amount, let rgb, let art):
                    if images[art] != nil {
                        HStack(spacing: 2) {
                            icon(art, original: original)
                            Text(verbatim: String(amount)).bold().foregroundColor(Color(red: Double((rgb >> 16) & 255) / 255,
                                green: Double((rgb >> 8) & 255) / 255, blue: Double(rgb & 255) / 255))
                        }.fixedSize()
                    } else {
                        Text(verbatim: original).bold().foregroundColor(Color(red: Double((rgb >> 16) & 255) / 255,
                            green: Double((rgb >> 8) & 255) / 255, blue: Double(rgb & 255) / 255))
                    }
                }
            }
        }.font(.subheadline)
    }
    @ViewBuilder private func icon(_ key: ChatArtworkRequest, original: String) -> some View {
        if let art = images[key] {
            let ratio = max(0.25, min(4, art.first.size.width / max(1, art.first.size.height)))
            ChatAnimatedArtwork(artwork: art, animate: animate && !reduceMotion)
                .frame(width: iconHeight * ratio, height: iconHeight)
                .accessibilityLabel(Text(verbatim: original))
        } else { Text(verbatim: original) }
    }
}
