import SwiftUI
import UIKit

@MainActor
final class ChatAvatars: ObservableObject {
    typealias Resolver = @MainActor (UInt32) async -> URL?

    @Published private(set) var images: [UInt32: UIImage] = [:]
    private let cache: ChannelImageCache
    private let resolve: Resolver
    private var pending: [UInt32] = []
    private var worker: Task<Void, Never>?
    private var active = false
    private var attempted: [UInt32: TimeInterval] = [:]
    private var order: [UInt32] = []

    init(cache: ChannelImageCache, resolve: @escaping Resolver) {
        self.cache = cache
        self.resolve = resolve
    }

    func updateVisible(_ senders: [UInt32]) {
        var seen = Set<UInt32>()
        pending.removeAll(keepingCapacity: true)
        for sender in senders where seen.insert(sender).inserted {
            pending.append(sender)
            if pending.count == 24 { break }
        }
        startIfNeeded()
    }

    func setActive(_ value: Bool) {
        active = value
        if value {
            startIfNeeded()
        } else {
            worker?.cancel()
        }
    }

    private func nextSender() -> UInt32? {
        let now = ProcessInfo.processInfo.systemUptime
        return pending.first { id in
            images[id] == nil && attempted[id].map { now - $0 >= 90 } != false
        }
    }

    private func startIfNeeded() {
        guard active, worker == nil, nextSender() != nil else { return }
        worker = Task {
            // Keep one worker across visible-row updates. A fast chat should
            // not repeatedly cancel an in-flight lookup before it can finish.
            while active, !Task.isCancelled, let sender = nextSender() {
                let url = await resolve(sender)
                let image: UIImage?
                if let url, !Task.isCancelled { image = await cache.loadChatAvatar(url: url) }
                else { image = nil }
                guard active, !Task.isCancelled else { break }

                if let image { images[sender] = image }
                attempted[sender] = ProcessInfo.processInfo.systemUptime
                order.removeAll { $0 == sender }
                order.append(sender)
                if order.count > 96 {
                    let expired = order.removeFirst()
                    attempted.removeValue(forKey: expired)
                    images.removeValue(forKey: expired)
                }
                try? await Task.sleep(nanoseconds: 650_000_000)
            }
            worker = nil
            // The view may have reactivated while a cancelled request unwound.
            if Task.isCancelled { startIfNeeded() }
        }
    }
}
