import Foundation

// Guest IRC is a public read path. The only outbound commands negotiate the
// connection, join one room, and answer keepalives.
enum TwitchGuestChat {
    enum Status: Equatable, Sendable { case connecting, listening, reconnecting, unavailable }
    enum Update: Sendable {
        case status(Status)
        case events([TwitchChatEvent])
    }
    private enum End {
        case retry(joined: Bool)
        case unavailable
    }

    private static let endpoint = URL(string: "wss://irc-ws.chat.twitch.tv:443")!

    static func listen(channel: String, update: @escaping @MainActor (Update) -> Void) async {
        guard let channel = TwitchChatMessages.normalizedLogin(channel) else {
            await update(.status(.unavailable))
            return
        }

        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpShouldSetCookies = false
        configuration.httpCookieStorage = nil
        configuration.urlCredentialStorage = nil
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel() }
        var retrySeconds: UInt64 = 1
        await update(.status(.connecting))
        while !Task.isCancelled {
            let socket = session.webSocketTask(with: endpoint)
            socket.maximumMessageSize = 64 * 1024
            let ended = await withTaskCancellationHandler {
                guard !Task.isCancelled else { return End.retry(joined: false) }
                socket.resume()
                return await read(socket, channel: channel, update: update)
            } onCancel: {
                socket.cancel(with: .goingAway, reason: nil)
            }
            socket.cancel(with: .goingAway, reason: nil)
            guard !Task.isCancelled else { return }
            switch ended {
            case .unavailable:
                await update(.status(.unavailable))
                return
            case .retry(let joined):
                if joined { retrySeconds = 1 }
                await update(.status(.reconnecting))
                do { try await Task.sleep(nanoseconds: retrySeconds * 1_000_000_000) }
                catch { return }
                retrySeconds = min(retrySeconds * 2, 16)
            }
        }
    }

    private static func read(_ socket: URLSessionWebSocketTask, channel: String,
                             update: @escaping @MainActor (Update) -> Void) async -> End {
        var welcomed = false
        var joined = false
        let registrationDeadline = Task {
            do { try await Task.sleep(nanoseconds: 12_000_000_000) }
            catch { return }
            socket.cancel(with: .goingAway, reason: nil)
        }
        defer { registrationDeadline.cancel() }
        do {
            try await socket.send(.string("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n"))
            let guest = Int.random(in: 100_000_000...999_999_999)
            try await socket.send(.string("NICK justinfan\(guest)\r\n"))
            while !Task.isCancelled {
                guard case .string(let text) = try await socket.receive() else { continue }
                let events = TwitchChatMessages.parse(text, channel: channel)
                var transcriptUpdates: [TwitchChatEvent] = []
                for event in events {
                    switch event {
                    case .welcome:
                        if !welcomed {
                            welcomed = true
                            try await socket.send(.string("JOIN #\(channel)\r\n"))
                        }
                    case .ping(let payload):
                        try await socket.send(.string("PONG :\(payload)\r\n"))
                    case .joined:
                        if !joined {
                            joined = true
                            registrationDeadline.cancel()
                            await update(.status(.listening))
                        }
                    case .unavailable: return .unavailable
                    case .reconnect: return .retry(joined: joined)
                    case .message, .removeMessage, .clear:
                        if joined { transcriptUpdates.append(event) }
                    }
                }
                if !transcriptUpdates.isEmpty, !Task.isCancelled {
                    await update(.events(transcriptUpdates))
                }
            }
        } catch {
            // Reconnect without surfacing transport payloads or account data.
        }
        return .retry(joined: joined)
    }
}
