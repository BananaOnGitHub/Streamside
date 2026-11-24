import Foundation

struct TwitchChatMessage: Identifiable, Equatable, Sendable {
    let id: String
    let login: String
    let displayName: String
    let color: UInt32?
    let body: String

    var author: String {
        if displayName.isEmpty { return login }
        if displayName.caseInsensitiveCompare(login) == .orderedSame { return displayName }
        return "\(displayName) (\(login))"
    }
}

enum TwitchChatEvent: Equatable, Sendable {
    case welcome, joined, unavailable, reconnect
    case ping(String)
    case message(TwitchChatMessage)
    case removeMessage(String)
    case clear(login: String?)
}

enum TwitchChatMessages {
    static func normalizedLogin(_ value: String) -> String? {
        guard (1...25).contains(value.utf8.count),
              value.utf8.allSatisfy({ (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || $0 == 95 })
        else { return nil }
        return value.lowercased()
    }

    static func parse(_ frame: String, channel: String) -> [TwitchChatEvent] {
        guard frame.utf8.count <= 64 * 1024, let channel = normalizedLogin(channel) else { return [] }
        let room = "#" + channel
        return frame.unicodeScalars.split(whereSeparator: { $0.value == 10 || $0.value == 13 })
            .compactMap { parseLine(String($0), room: room) }
    }

    private static func parseLine(_ line: String, room: String) -> TwitchChatEvent? {
        guard line.utf8.count <= 8192 else { return nil }
        var rest = line[...]
        var tags: [Substring: Substring] = [:]
        if rest.first == "@", let space = rest.firstIndex(of: " ") {
            for item in rest[rest.index(after: rest.startIndex)..<space].split(separator: ";") {
                if let equals = item.firstIndex(of: "=") {
                    tags[item[..<equals]] = item[item.index(after: equals)...]
                }
            }
            rest = rest[rest.index(after: space)...]
        }

        var prefix: Substring = ""
        if rest.first == ":", let space = rest.firstIndex(of: " ") {
            prefix = rest[rest.index(after: rest.startIndex)..<space]
            rest = rest[rest.index(after: space)...]
        }

        let separator = rest.range(of: " :")
        let body = separator.map { rest[$0.upperBound...] }
        let words = (separator.map { rest[..<$0.lowerBound] } ?? rest).split(separator: " ")
        guard let command = words.first else { return nil }
        let destination = words.dropFirst().first

        switch command {
        case "001": return .welcome
        case "PING":
            guard let payload = body ?? destination, !payload.isEmpty else { return nil }
            return .ping(String(payload))
        case "RECONNECT": return .reconnect
        case "CAP": return words.contains("NAK") ? .unavailable : nil
        case "NOTICE":
            let denied = ["msg_banned", "msg_channel_suspended", "msg_room_not_found", "no_permission"]
            if destination == "*" || (destination == room && denied.contains(String(tags["msg-id"] ?? ""))) {
                return .unavailable
            }
            return nil
        case "ROOMSTATE": return destination == room ? .joined : nil
        case "PRIVMSG":
            guard destination == room, let rawBody = body, !rawBody.isEmpty,
                  let rawLogin = prefix.split(separator: "!", maxSplits: 1).first,
                  let login = normalizedLogin(String(rawLogin)), let id = identifier(tags["id"]) else { return nil }
            let text = rawBody.hasPrefix("\u{1}ACTION ") && rawBody.hasSuffix("\u{1}")
                ? rawBody.dropFirst(8).dropLast() : rawBody
            guard !text.isEmpty else { return nil }
            return .message(TwitchChatMessage(id: id, login: login, displayName: displayName(tags["display-name"] ?? ""),
                                              color: color(tags["color"]), body: String(text)))
        case "CLEARMSG":
            guard destination == room, let id = identifier(tags["target-msg-id"]) else { return nil }
            return .removeMessage(id)
        case "CLEARCHAT":
            guard destination == room else { return nil }
            guard let body else { return .clear(login: nil) }
            return normalizedLogin(String(body)).map { .clear(login: $0) }
        default: return nil
        }
    }

    private static func identifier(_ value: Substring?) -> String? {
        guard let value, (1...64).contains(value.utf8.count) else { return nil }
        return String(value)
    }

    private static func color(_ value: Substring?) -> UInt32? {
        guard let value, value.utf8.count == 7, value.first == "#" else { return nil }
        let hex = value.dropFirst()
        guard hex.utf8.allSatisfy({ (48...57).contains($0) || (65...70).contains($0) || (97...102).contains($0) }) else { return nil }
        return UInt32(hex, radix: 16)
    }

    private static func displayName(_ value: Substring) -> String {
        var name = ""
        var escaped = false
        for scalar in value.unicodeScalars {
            if escaped {
                switch scalar {
                case "s": name.append(" ")
                case ":": name.append(";")
                case "r", "n": break
                default: name.unicodeScalars.append(scalar)
                }
                escaped = false
            } else if scalar == "\\" {
                escaped = true
            } else if !CharacterSet.controlCharacters.contains(scalar) {
                name.unicodeScalars.append(scalar)
            }
        }
        return String(name.trimmingCharacters(in: .whitespaces).prefix(64))
    }
}

struct TwitchChatTranscript {
    private(set) var messages: [TwitchChatMessage] = []
    private static let limit = 200

    mutating func apply(_ events: [TwitchChatEvent]) {
        for event in events {
            switch event {
            case .message(let message):
                guard !messages.contains(where: { $0.id == message.id }) else { continue }
                messages.append(message)
                if messages.count > Self.limit { messages.removeFirst(messages.count - Self.limit) }
            case .removeMessage(let id):
                messages.removeAll { $0.id == id }
            case .clear(let login):
                if let login { messages.removeAll { $0.login == login } }
                else { messages.removeAll() }
            default: break
            }
        }
    }
}
