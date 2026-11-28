import Foundation

struct ChatEmoteSpan: Equatable, Sendable {
    let id: String
    let start: Int
    let end: Int // inclusive Unicode scalar offsets from Twitch IRC
}

struct ChatArtworkRequest: Hashable, Sendable {
    let animated: URL?
    let still: URL?
    static func allowed(_ url: URL) -> Bool {
        guard let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              parts.scheme == "https", parts.user == nil, parts.password == nil,
              parts.port == nil, parts.query == nil, parts.fragment == nil,
              let host = parts.host?.lowercased() else { return false }
        return host == "static-cdn.jtvnw.net" || host == "d3aqoihi2n8ty8.cloudfront.net"
    }
    static func emote(_ id: String, dark: Bool) -> Self? {
        guard ChatRichText.validID(id) else { return nil }
        let base = "https://static-cdn.jtvnw.net/emoticons/v2/\(id)/"
        let suffix = "/\(dark ? "dark" : "light")/2.0"
        return Self(animated: URL(string: base + "animated" + suffix),
                    still: URL(string: base + "static" + suffix))
    }
}

struct ChatCheerCatalogue: Equatable, Sendable {
    struct Entry: Equatable, Sendable {
        let prefix: String
        let template: String
        let tiers: [Int]
    }
    var entries: [String: Entry] = [:]
    var colors: [Int: UInt32] = [:]

    mutating func merge(_ data: [String: Any]) {
        for group in (data["groups"] as? [[String: Any]] ?? []).prefix(256) {
            guard let prefix = group["prefix"] as? String, ChatRichText.validPrefix(prefix),
                  let template = group["template"] as? String, template.utf8.count <= 2048,
                  let tiers = group["tiers"] as? [Int], tiers.count <= 32 else { continue }
            let valid = Array(Set(tiers.filter { (1...100_000_000).contains($0) })).sorted()
            if !valid.isEmpty {
                let entry = Entry(prefix: prefix.lowercased(), template: template, tiers: valid)
                // Reject unrecognized URL templates before matching any cheer.
                if artwork(entry, tier: valid[0], dark: true) != nil { entries[entry.prefix] = entry }
            }
        }
        for row in (data["colors"] as? [[String: Any]] ?? []).prefix(64) {
            guard let bits = row["bits"] as? Int, (1...100_000_000).contains(bits),
                  let color = row["color"] as? String else { continue }
            let hex = color.first == "#" ? String(color.dropFirst()) : color
            guard hex.utf8.count == 6, let rgb = UInt32(hex, radix: 16) else { continue }
            colors[bits] = rgb
        }
    }

    func cheer(_ token: String, dark: Bool) -> (Int, UInt32, ChatArtworkRequest)? {
        let lower = token.lowercased()
        let digits = lower.utf8.reversed().prefix { (48...57).contains($0) }.count
        guard digits > 0, digits < lower.utf8.count else { return nil }
        // Prefer the longest known prefix when it itself ends in digits.
        for length in 1...min(9, digits) {
            let suffix = lower.suffix(length)
            guard let entry = entries[String(lower.dropLast(length))],
                  let amount = Int(suffix), (1...100_000_000).contains(amount),
                  let tier = entry.tiers.last(where: { $0 <= amount }),
                  let art = artwork(entry, tier: tier, dark: dark) else { continue }
            return (amount, colors[tier] ?? 0x979797, art)
        }
        return nil
    }

    private func artwork(_ entry: Entry, tier: Int, dark: Bool) -> ChatArtworkRequest? {
        func url(animated: Bool) -> URL? {
            let substitutions = ["PREFIX": entry.prefix, "BACKGROUND": dark ? "dark" : "light",
                                 "ANIMATION": animated ? "animated" : "static", "TIER": String(tier),
                                 "SCALE": "2", "EXTENSION": animated ? "gif" : "png"]
            var text = entry.template
            for (key, value) in substitutions { text = text.replacingOccurrences(of: key, with: value) }
            guard let result = URL(string: text), ChatArtworkRequest.allowed(result) else { return nil }
            return result
        }
        let request = ChatArtworkRequest(animated: url(animated: true), still: url(animated: false))
        return request.animated != nil || request.still != nil ? request : nil
    }
}

enum ChatRichText {
    enum Part: Equatable, Sendable {
        case text(String)
        case emote(String, ChatArtworkRequest)
        case cheer(String, Int, UInt32, ChatArtworkRequest)
        var artwork: ChatArtworkRequest? {
            switch self {
            case .text: return nil
            case .emote(_, let art), .cheer(_, _, _, let art): return art
            }
        }
    }
    static func validID(_ id: String) -> Bool {
        (1...80).contains(id.utf8.count) && id.utf8.allSatisfy {
            (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || $0 == 95 || $0 == 45
        }
    }
    static func validPrefix(_ value: String) -> Bool {
        (1...64).contains(value.utf8.count) && value.utf8.allSatisfy {
            (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || $0 == 95
        }
    }
    static func spans(_ tag: Substring?, body: String) -> [ChatEmoteSpan] {
        guard let tag, tag.utf8.count <= 4096 else { return [] }
        let count = body.unicodeScalars.count
        var spans: [ChatEmoteSpan] = []
        for group in tag.split(separator: "/") {
            let components = group.split(separator: ":", maxSplits: 1)
            guard components.count == 2, validID(String(components[0])) else { continue }
            for range in components[1].split(separator: ",") {
                let pair = range.split(separator: "-", maxSplits: 1)
                guard pair.count == 2, let start = Int(pair[0]), let end = Int(pair[1]),
                      start >= 0, end >= start, end < count else { continue }
                spans.append(ChatEmoteSpan(id: String(components[0]), start: start, end: end))
                if spans.count > 64 { return [] }
            }
        }
        let sorted = spans.sorted { $0.start < $1.start }
        for pair in zip(sorted, sorted.dropFirst()) where pair.0.end >= pair.1.start { return [] }
        return sorted
    }
    static func parts(_ message: TwitchChatMessage, catalogue: ChatCheerCatalogue, dark: Bool) -> [Part] {
        if message.emotes.isEmpty && message.bits == 0 { return [.text(message.body)] }
        let scalars = Array(message.body.unicodeScalars)
        func slice(_ lower: Int, _ upper: Int) -> String { String(String.UnicodeScalarView(scalars[lower..<upper])) }
        var base: [Part] = [], cursor = 0
        for span in message.emotes {
            guard span.start >= cursor, span.end >= span.start, span.end < scalars.count,
                  let art = ChatArtworkRequest.emote(span.id, dark: dark) else { continue }
            if cursor < span.start { base.append(.text(slice(cursor, span.start))) }
            base.append(.emote(slice(span.start, span.end + 1), art))
            cursor = span.end + 1
        }
        if cursor < scalars.count { base.append(.text(slice(cursor, scalars.count))) }
        guard message.bits > 0 else { return base }
        var parsed: [Part] = [], sum = 0
        for part in base {
            guard case .text(let text) = part else { parsed.append(part); continue }
            // Preserve whitespace and punctuation. Only whole server-verified
            // cheer tokens can be replaced; an ordinary "Cheer100" stays text.
            for word in words(text) {
                if let (amount, rgb, art) = catalogue.cheer(word, dark: dark), amount <= message.bits - sum {
                    sum += amount
                    parsed.append(.cheer(word, amount, rgb, art))
                } else { parsed.append(.text(word)) }
            }
        }
        return sum == message.bits ? parsed : base
    }
    static func words(_ text: String) -> [String] {
        var result: [String] = [], current = "", whitespace: Bool?
        for ch in text {
            let isSpace = ch.isWhitespace
            if whitespace != nil && whitespace != isSpace { result.append(current); current = "" }
            current.append(ch); whitespace = isSpace
        }
        if !current.isEmpty { result.append(current) }
        return result
    }
}
