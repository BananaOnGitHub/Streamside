import Combine
import CoreHaptics
import Foundation
import UIKit

// One lazily created haptics-only engine. No audio-session category changes,
// background playback, device-model intensity guesses, or per-row engines.
@MainActor
final class TitleHaptics {
    private var engine: CHHapticEngine?
    private var player: CHHapticPatternPlayer?
    private var pending: Task<Void, Never>?
    private var owner: UUID?
    private var generation = UUID()
    private var lifecycle: AnyCancellable?
    private let impact = UIImpactFeedbackGenerator(style: .medium)

    init() {
        lifecycle = NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)
            .receive(on: RunLoop.main).sink { [weak self] _ in
                self?.cancelAll()
                self?.engine?.stop(completionHandler: nil)
            }
    }
    func begin(owner: UUID) {
        cancelAll()
        guard UIApplication.shared.applicationState == .active else { return }
        self.owner = owner
        impact.prepare()
        // Do not rumble on ordinary taps or the beginning of a scroll.
        pending = Task { [weak self] in
            do { try await Task.sleep(nanoseconds: 150_000_000) } catch { return }
            guard let self, self.owner == owner else { return }
            self.playRamp(owner: owner)
        }
    }
    func cancel(owner: UUID) {
        if self.owner == owner { cancelAll() }
    }
    func opened() {
        cancelAll()
        guard UIApplication.shared.applicationState == .active else { return }
        impact.impactOccurred(intensity: 0.65)
    }
    private func cancelAll() {
        generation = UUID()
        pending?.cancel(); pending = nil; owner = nil
        try? player?.stop(atTime: CHHapticTimeImmediate)
        player = nil
    }
    static func rampPattern() throws -> CHHapticPattern {
        let event = CHHapticEvent(eventType: .hapticContinuous, parameters: [
            .init(parameterID: .hapticIntensity, value: 1),
            .init(parameterID: .hapticSharpness, value: 0.15)
        ], relativeTime: 0, duration: 0.85)
        let curve = CHHapticParameterCurve(parameterID: .hapticIntensityControl, controlPoints: [
            .init(relativeTime: 0, value: 0.04),
            .init(relativeTime: 0.85, value: 0.18)
        ], relativeTime: 0)
        return try CHHapticPattern(events: [event], parameterCurves: [curve])
    }
    private func playRamp(owner: UUID) {
        guard CHHapticEngine.capabilitiesForHardware().supportsHaptics,
              self.owner == owner, UIApplication.shared.applicationState == .active else { return }
        do {
            if engine == nil {
                let engine = try CHHapticEngine()
                engine.playsHapticsOnly = true
                engine.isAutoShutdownEnabled = true
                engine.stoppedHandler = { [weak self] _ in
                    Task { @MainActor [weak self] in self?.cancelAll() }
                }
                engine.resetHandler = { [weak self] in
                    Task { @MainActor [weak self] in
                        self?.cancelAll(); self?.engine = nil
                    }
                }
                self.engine = engine
            }
            guard let engine else { return }
            let engineID = ObjectIdentifier(engine)
            let requestGeneration = generation
            engine.start { [weak self] error in
                let started = error == nil
                Task { @MainActor [weak self] in
                    guard let self, let engine = self.engine, started,
                          ObjectIdentifier(engine) == engineID, self.generation == requestGeneration,
                          self.owner == owner, UIApplication.shared.applicationState == .active else { return }
                    do {
                        let player = try engine.makePlayer(with: Self.rampPattern())
                        try player.start(atTime: CHHapticTimeImmediate)
                        self.player = player
                    } catch { self.cancelAll() }
                }
            }
        } catch { cancelAll() }
    }
}
