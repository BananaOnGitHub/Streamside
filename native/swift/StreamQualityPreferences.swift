import Foundation

// Per-channel preference, never a manifest URL, SDK instance or account token.
// A missing rendition falls back to Auto without erasing the saved choice.
struct StreamQualityPreferences {
    static let key = "dev.streamside.player.channelQualities"
    let defaults: UserDefaults
    init(defaults: UserDefaults = .standard) { self.defaults = defaults }
    private func channelKey(_ channel: String) -> String? {
        let name = channel.lowercased()
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyz0123456789_")
        return !name.isEmpty && name.count <= 128 && name.unicodeScalars.allSatisfy(allowed.contains) ? name : nil
    }
    func selection(for channel: String) -> String {
        guard let channel = channelKey(channel), let value = defaults.dictionary(forKey: Self.key)?[channel] as? String,
              !value.isEmpty, value.count <= 128, value.lowercased() != "audio_only" else { return "auto" }
        return value
    }
    func save(_ value: String, for channel: String) {
        guard let channel = channelKey(channel), !value.isEmpty, value.count <= 128 else { return }
        var values = defaults.dictionary(forKey: Self.key) as? [String: String] ?? [:]
        values.removeValue(forKey: channel)
        if value != "auto" {
            while values.count >= 256, let first = values.keys.sorted().first { values.removeValue(forKey: first) }
            values[channel] = value
        }
        defaults.set(values, forKey: Self.key)
    }
}
