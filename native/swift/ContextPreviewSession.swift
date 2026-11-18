import UIKit

// The source-anchored presenter owns motion; this transaction owns media lifetime.
// The Watch action and video tap converge here; neither starts a
// second request or unmutes a preview during dismissal.
@MainActor
final class ContextPreviewSession {
    enum Phase { case prepared, visible, ending, transferred, cancelled }
    let id = UUID()
    let controller: UIViewController
    private(set) var phase = Phase.prepared
    private(set) var watchRequested = false
    var dismissPreview: (() -> Void)?
    var videoTapEnabled: () -> Bool = { true }
    private let claim: (UUID) -> Bool
    private let release: (UUID) -> Void
    private let valid: () -> Bool
    private let start: () -> Void
    private let stop: () -> Void
    private let handoff: () -> Bool
    private var stopped = false
    private var released = false
    private var observers: [NSObjectProtocol] = []

    init(controller: UIViewController, claim: @escaping (UUID) -> Bool,
         release: @escaping (UUID) -> Void, valid: @escaping () -> Bool,
         start: @escaping () -> Void, stop: @escaping () -> Void, handoff: @escaping () -> Bool) {
        self.controller = controller; self.claim = claim; self.release = release
        self.valid = valid; self.start = start; self.stop = stop; self.handoff = handoff
        let center = NotificationCenter.default
        observers.append(center.addObserver(forName: UIApplication.willResignActiveNotification, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { self?.cancel() }
        })
        observers.append(center.addObserver(forName: Notification.Name("SSNNativeServiceDidChange"), object: nil, queue: .main) { [weak self] _ in
            // Let the owned account snapshot and native player observe the same
            // notification before deciding whether this preview is still valid.
            Task { @MainActor [weak self] in
                guard let self, self.phase != .transferred else { return }
                if !self.valid() { self.cancel() }
            }
        })
    }
    @discardableResult func display() -> Bool {
        guard phase == .prepared else { return phase == .visible }
        guard valid(), claim(id) else { cancel(); return false }
        phase = .visible; start(); return true
    }
    func requestWatch() {
        guard phase == .visible || phase == .ending else { return }
        watchRequested = true
    }
    func end(after registerCompletion: (@escaping () -> Void) -> Void) {
        guard phase == .visible || phase == .prepared else { return }
        phase = .ending
        dismissPreview = nil // Presentation is already ending; never dismiss twice.
        let complete = { [self] in
            // The presenter detaches before we ask the guarded root to
            // present the theatre. One main-queue turn orders any late action
            // ahead of this final decision.
            DispatchQueue.main.async { self.completeEnd() }
        }
        registerCompletion(complete)
    }
    private func completeEnd() {
        guard phase == .ending else { return }
        if watchRequested && valid() {
            releaseOnce()
            if handoff() { phase = .transferred; dismissPreview = nil; return }
        }
        cancel()
    }
    func cancel() {
        guard phase != .transferred, phase != .cancelled else { return }
        phase = .cancelled
        stopOnce(); releaseOnce()
        let dismiss = dismissPreview; dismissPreview = nil; dismiss?()
    }
    private func stopOnce() { if !stopped { stopped = true; stop() } }
    private func releaseOnce() { if !released { released = true; release(id) } }
    deinit {
        observers.forEach(NotificationCenter.default.removeObserver)
        // A source row disappearing must never strand the facade's native timer.
        let transferred = phase == .transferred
        let needsStop = !stopped && !transferred
        let needsRelease = !released
        let stop = self.stop, release = self.release, id = self.id
        if needsStop || needsRelease {
            Task { @MainActor in
                if needsStop { stop() }
                if needsRelease { release(id) }
            }
        }
    }
}
