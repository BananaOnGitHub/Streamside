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
                        let receipt = ["passed": ticking && stopped && resumed, "ticking": ticking, "paused": stopped, "resumed": resumed]
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
