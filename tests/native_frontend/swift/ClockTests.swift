import Combine
import Foundation
import UIKit

@main @MainActor final class ClockTestDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    var clock: StreamClock?
    var observation: AnyCancellable?
    var updates = 0
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = UIViewController()
        window.makeKeyAndVisible(); self.window = window
        let label = StreamTitleLabel()
        label.font = .preferredFont(forTextStyle: .subheadline)
        label.lineBreakMode = .byTruncatingTail
        label.text = "Short"; label.numberOfLines = 1
        var titleMeasurement = !label.isTruncated(atWidth: 300)
        label.text = "First line\nSecond line"
        titleMeasurement = titleMeasurement && label.isTruncated(atWidth: 300)
        label.numberOfLines = 2
        titleMeasurement = titleMeasurement && !label.isTruncated(atWidth: 300)
        label.text = String(repeating: "Long title 👨‍👩‍👧‍👦 words ", count: 10)
        titleMeasurement = titleMeasurement && label.isTruncated(atWidth: 120)
        label.text = "مرحبا بالعالم 👋"; label.numberOfLines = 1
        titleMeasurement = titleMeasurement && label.isTruncated(atWidth: 25) && !label.isTruncated(atWidth: 1000)
        label.font = .preferredFont(forTextStyle: .subheadline, compatibleWith: UITraitCollection(preferredContentSizeCategory: .accessibilityExtraExtraExtraLarge))
        label.text = "First line\nSecond line"; label.numberOfLines = 2
        titleMeasurement = titleMeasurement && !label.isTruncated(atWidth: 1000) && label.isTruncated(atWidth: 70)
        let measuredTitles = titleMeasurement
        let hapticPattern = (try? TitleHaptics.rampPattern()).map { abs($0.duration - 0.85) < 0.001 } ?? false
        let clock = StreamClock(); self.clock = clock
        observation = clock.$now.dropFirst().sink { [weak self] _ in self?.updates += 1 }
        let start = Date()
        NotificationCenter.default.post(name: UIApplication.didBecomeActiveNotification, object: application)
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.4) {
            let ticking = self.updates >= 2 && clock.now.timeIntervalSince(start) >= 1
            NotificationCenter.default.post(name: UIApplication.willResignActiveNotification, object: application)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                let paused = clock.now
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.3) {
                    let stopped = clock.now == paused
                    NotificationCenter.default.post(name: UIApplication.didBecomeActiveNotification, object: application)
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                        let resumed = clock.now.timeIntervalSince(paused) >= 1
                        let receipt = ["passed": ticking && stopped && resumed && measuredTitles && hapticPattern, "ticking": ticking, "paused": stopped, "resumed": resumed, "title_measurement": measuredTitles, "haptic_pattern": hapticPattern]
                        let path = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("clock-test.json")
                        try! JSONSerialization.data(withJSONObject: receipt).write(to: path)
                        exit(receipt["passed"]! ? 0 : 1)
                    }
                }
            }
        }
        return true
    }
}
