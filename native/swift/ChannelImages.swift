import Foundation
import UIKit
import ImageIO
import UniformTypeIdentifiers

// Dedicated unauthenticated image session. Native GraphQL supplies the URLs;
// cookies, credentials and Twitch's authenticated networking are never attached.
private final class ImageRedirectPolicy: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest,
                    completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(request.url.map(ChannelImagePolicy.allowed) == true ? request : nil)
    }
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        // TLS server-trust evaluation remains the system's responsibility.
        completionHandler(challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust
                          ? .performDefaultHandling : .cancelAuthenticationChallenge, nil)
    }
}

// The native viewer and menu share this file. Keep the CDN bytes for zoom
// and sharing, and release the temporary directory when both are finished.
final class ProfileArtworkFile: Identifiable {
    var id: URL { fileURL }
    let source: URL
    let fileURL: URL
    let preview: UIImage

    init(source: URL, data: Data, type: UTType, title: String, preview: UIImage) throws {
        self.source = source
        self.preview = preview
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        fileURL = directory.appendingPathComponent(title).appendingPathExtension(type.preferredFilenameExtension ?? "image")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        do { try data.write(to: fileURL, options: .atomic) }
        catch {
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    deinit { try? FileManager.default.removeItem(at: fileURL.deletingLastPathComponent()) }
}

actor ChannelImageCache {
    private let cache = NSCache<NSString, UIImage>()
    private let session: URLSession
    init(protocolClasses: [AnyClass]? = nil) {
        let configuration = URLSessionConfiguration.ephemeral
        if let protocolClasses { configuration.protocolClasses = protocolClasses }
        configuration.httpShouldSetCookies = false
        configuration.httpCookieStorage = nil
        configuration.urlCredentialStorage = nil
        configuration.httpMaximumConnectionsPerHost = 3
        configuration.timeoutIntervalForRequest = 5
        configuration.timeoutIntervalForResource = 5
        configuration.urlCache = URLCache(memoryCapacity: 12 * 1024 * 1024, diskCapacity: 0, diskPath: nil)
        session = URLSession(configuration: configuration, delegate: ImageRedirectPolicy(), delegateQueue: nil)
        cache.totalCostLimit = 24 * 1024 * 1024
        cache.countLimit = 96
    }
    private func key(url: URL, generation: UInt64, avatar: Bool) -> NSString {
        "\(generation)|\(avatar)|\(url.absoluteString)" as NSString
    }

    func cachedImage(url: URL, generation: UInt64, avatar: Bool) -> UIImage? {
        cache.object(forKey: key(url: url, generation: generation, avatar: avatar))
    }

    func load(url: URL, generation: UInt64, avatar: Bool) async -> UIImage? {
        guard ChannelImagePolicy.allowed(url), !Task.isCancelled else { return nil }
        let key = key(url: url, generation: generation, avatar: avatar)
        if let image = cache.object(forKey: key) { return image }
        var request = URLRequest(url: url, cachePolicy: .reloadRevalidatingCacheData, timeoutInterval: 5)
        request.httpShouldHandleCookies = false
        do {
            let (data, response) = try await session.data(for: request)
            guard !Task.isCancelled, let response = response as? HTTPURLResponse,
                  response.statusCode == 200, response.url.map(ChannelImagePolicy.allowed) == true,
                  data.count <= 2 * 1024 * 1024,
                  let mime = response.mimeType, mime.hasPrefix("image/"),
                  let source = CGImageSourceCreateWithData(data as CFData, nil) else { return nil }
            let options: [CFString: Any] = [kCGImageSourceCreateThumbnailFromImageAlways: true,
                                           kCGImageSourceCreateThumbnailWithTransform: true,
                                           kCGImageSourceThumbnailMaxPixelSize: avatar ? 80 : 480,
                                           kCGImageSourceShouldCacheImmediately: true]
            guard let cgImage = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary),
                  !Task.isCancelled else { return nil }
            let image = UIImage(cgImage: cgImage)
            cache.setObject(image, forKey: key, cost: cgImage.bytesPerRow * cgImage.height)
            return image
        } catch { return nil } // Cancellation/offline/timeout use a stable placeholder; no retry storm.
    }

    func loadProfileArtwork(url: URL, avatar: Bool, title: String) async -> ProfileArtworkFile? {
        guard ChannelImagePolicy.allowed(url), !Task.isCancelled else { return nil }
        var candidates = [url]
        if avatar, let larger = ChannelImagePolicy.largerProfileAvatar(url) { candidates.insert(larger, at: 0) }
        for candidate in candidates {
            guard !Task.isCancelled else { return nil }
            if let file = await profileArtwork(from: candidate, sourceURL: url, title: title) { return file }
        }
        return nil
    }

    private func profileArtwork(from url: URL, sourceURL: URL, title: String) async -> ProfileArtworkFile? {
        var request = URLRequest(url: url, timeoutInterval: 5)
        request.httpShouldHandleCookies = false
        do {
            let (data, response) = try await session.data(for: request)
            guard !Task.isCancelled, let response = response as? HTTPURLResponse, response.statusCode == 200,
                  response.url.map(ChannelImagePolicy.allowed) == true, response.mimeType?.hasPrefix("image/") == true,
                  data.count <= 12 * 1024 * 1024,
                  let source = CGImageSourceCreateWithData(data as CFData, nil),
                  let identifier = CGImageSourceGetType(source) as String?, let type = UTType(identifier),
                  type.conforms(to: .image), type.preferredFilenameExtension != nil,
                  let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
                  let width = properties[kCGImagePropertyPixelWidth] as? Int, (1...8192).contains(width),
                  let height = properties[kCGImagePropertyPixelHeight] as? Int, (1...8192).contains(height),
                  width * height <= 24_000_000 else { return nil }
            let options: [CFString: Any] = [kCGImageSourceCreateThumbnailFromImageAlways: true,
                                           kCGImageSourceCreateThumbnailWithTransform: true,
                                           kCGImageSourceThumbnailMaxPixelSize: 1200,
                                           kCGImageSourceShouldCacheImmediately: true]
            guard let thumbnail = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary),
                  !Task.isCancelled else { return nil }
            return try ProfileArtworkFile(source: sourceURL, data: data, type: type, title: title, preview: UIImage(cgImage: thumbnail))
        } catch { return nil }
    }
}
