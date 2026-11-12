import SwiftUI
import UIKit

// Twitch retains its UIApplication/scene delegates, native bootstrap and window.
// The window gesture remains available if Twitch later replaces our root.
@objc(SSNSwiftUIHost)
@MainActor
public final class SSNSwiftUIHost: NSObject {
    private static var window: UIWindow?
    private static var services: NativeServices?
    private static weak var nativeController: UIViewController?
    private static var diagnosticsController: UIViewController?
    private static var gestureTarget: SSNSwiftUIHost?
    private static var baseline = false

    // Ownership is not a runtime classification: another root can be native UIKit.
    @objc public static func rootOwner() -> Int {
        guard let window else { return 0 }
        guard let root = window.rootViewController else { return 3 }
        return root === nativeController ? 1 : 2
    }

    @objc(attachToWindow:)
    public static func attach(to window: UIWindow) {
        guard self.window == nil else { return }
        self.window = window
        let services = NativeServices()
        self.services = services
        let native = (SSNNativeBridge.shared().snapshot()["nativeMode"] as? NSNumber)?.boolValue ?? false
        if native {
            let controller = UIHostingController(rootView: StreamsideShell(services: services))
            nativeController = controller
            window.rootViewController = controller
        }
        let target = SSNSwiftUIHost()
        gestureTarget = target
        baseline = !native
        let gesture = UILongPressGestureRecognizer(target: target, action: #selector(openDiagnostics(_:)))
        gesture.numberOfTouchesRequired = 2
        gesture.minimumPressDuration = 1
        gesture.cancelsTouchesInView = false
        gesture.delaysTouchesBegan = false
        gesture.delaysTouchesEnded = false
        window.addGestureRecognizer(gesture)
        SSNSwiftUIReady()
    }

    @objc private func openDiagnostics(_ gesture: UILongPressGestureRecognizer) {
        guard gesture.state == .began, let services = Self.services,
              var presenter = Self.window?.rootViewController else { return }
        if Self.diagnosticsController == nil {
            Self.diagnosticsController = UIHostingController(rootView: DiagnosticsView(services: services, baseline: Self.baseline))
        }
        guard let controller = Self.diagnosticsController,
              controller.presentingViewController == nil else { return }
        while let next = presenter.presentedViewController { presenter = next }
        guard !presenter.isBeingPresented, !presenter.isBeingDismissed else { return }
        Self.services?.reloadSnapshot()
        presenter.present(controller, animated: true)
    }
}
