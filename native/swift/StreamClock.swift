import Combine
import Foundation
import UIKit

// One clock for visible duration pills. UIKit owns this application's lifecycle;
// a SwiftUI Scene is not created by the injected UIHostingController.
@MainActor
final class StreamClock: ObservableObject {
    @Published private(set) var now = Date()
    private var timer: Timer?
    private var lifecycle: [AnyCancellable] = []

    init() {
        lifecycle = [
            NotificationCenter.default.publisher(for: UIApplication.didBecomeActiveNotification)
                .receive(on: RunLoop.main).sink { [weak self] _ in self?.setActive(true) },
            NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)
                .receive(on: RunLoop.main).sink { [weak self] _ in self?.setActive(false) }
        ]
        setActive(UIApplication.shared.applicationState == .active)
    }

    func setActive(_ active: Bool) {
        timer?.invalidate(); timer = nil
        guard active else { return }
        now = Date() // Catch up immediately after suspension; never count ticks.
        let timer = Timer(timeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in self?.now = Date() }
        }
        RunLoop.main.add(timer, forMode: .common)
        self.timer = timer
    }

    deinit { timer?.invalidate() }
}
