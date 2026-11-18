import Foundation
import Combine

// Owns consent, never a player. Loading CCL metadata cannot start media/audio.
@MainActor
final class MarkedContentGate: ObservableObject {
    enum Stage { case loading, warning, failed, thumbnails, finished }
    @Published private(set) var stage = Stage.loading
    @Published private(set) var labels: [String] = []
    @Published var dontShowAgain = false
    private let load: () async -> [String]?
    private let valid: () -> Bool
    private let saveWarnings: (Bool) -> Void
    private let thumbnailsEnabled: () -> Bool
    private let saveThumbnails: (Bool) -> Void
    private var completion: ((Bool) -> Void)?
    private var task: Task<Void, Never>?

    init(load: @escaping () async -> [String]?, valid: @escaping () -> Bool,
         saveWarnings: @escaping (Bool) -> Void, saveThumbnails: @escaping (Bool) -> Void,
         thumbnailsEnabled: @escaping () -> Bool = { false }, completion: @escaping (Bool) -> Void) {
        self.load = load; self.valid = valid; self.saveWarnings = saveWarnings
        self.saveThumbnails = saveThumbnails; self.thumbnailsEnabled = thumbnailsEnabled; self.completion = completion
    }
    func start() {
        guard completion != nil, stage == .loading || stage == .failed else { return }
        guard valid() else { close(); return }
        task?.cancel(); stage = .loading
        task = Task { [weak self, load] in
            let labels = await load()
            guard !Task.isCancelled, let self, self.completion != nil else { return }
            guard self.valid() else { self.close(); return }
            if let labels, !labels.isEmpty {
                self.labels = labels; self.stage = .warning
            } else { self.stage = .failed }
        }
    }
    func proceed() {
        guard stage == .warning, valid() else { close(); return }
        switch MarkedContentPreferences.decision(continuing: true, dontShowAgain: dontShowAgain) {
        case .askThumbnails:
            saveWarnings(false)
            if thumbnailsEnabled() { finish(true) }
            else { stage = .thumbnails }
        case .play: finish(true)
        case .cancel: close()
        }
    }
    func chooseThumbnails(_ enabled: Bool) {
        guard stage == .thumbnails, valid() else { close(); return }
        saveThumbnails(enabled); finish(true)
    }
    func close() { finish(false) }
    private func finish(_ accepted: Bool) {
        guard let completion else { return }
        self.completion = nil; task?.cancel(); task = nil; stage = .finished
        completion(accepted)
    }
}
