import Foundation
import UIKit
import ImageIO

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

actor ChannelImageCache {
    private let cache = NSCache<NSString, UIImage>()
    private let session: URLSession
    init() {
        let configuration = URLSessionConfiguration.ephemeral
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
    func load(url: URL, generation: UInt64, avatar: Bool) async -> UIImage? {
        guard ChannelImagePolicy.allowed(url), !Task.isCancelled else { return nil }
        let key = "\(generation)|\(avatar)|\(url.absoluteString)" as NSString
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
}
