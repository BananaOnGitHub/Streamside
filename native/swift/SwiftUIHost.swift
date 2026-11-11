import SwiftUI
import UIKit

// Twitch retains its UIApplication/scene delegates, native bootstrap and window.
// SwiftUI owns the replacement root content and all navigation inside that root.
@objc(SSNSwiftUIHost)
@MainActor
public final class SSNSwiftUIHost: NSObject {
    private static var window: UIWindow?
    private static var services: NativeServices?
    private static var baselineController: UIViewController?
    private static var gestureTarget: SSNSwiftUIHost?

    @objc(attachToWindow:)
    public static func attach(to window: UIWindow) {
        guard self.window == nil else { return }
        self.window = window
        let services = NativeServices()
        self.services = services
        let native = (SSNNativeBridge.shared().snapshot()["nativeMode"] as? NSNumber)?.boolValue ?? false
        if native {
            window.rootViewController = UIHostingController(rootView: StreamsideShell(services: services))
        } else {
            let target = SSNSwiftUIHost()
            gestureTarget = target
            baselineController = UIHostingController(rootView: DiagnosticsView(services: services, baseline: true))
            let gesture = UILongPressGestureRecognizer(target: target, action: #selector(openBaseline(_:)))
            gesture.numberOfTouchesRequired = 2
            gesture.minimumPressDuration = 1
            gesture.cancelsTouchesInView = false
            gesture.delaysTouchesBegan = false
            gesture.delaysTouchesEnded = false
            window.addGestureRecognizer(gesture)
        }
        SSNSwiftUIReady()
    }

    @objc private func openBaseline(_ gesture: UILongPressGestureRecognizer) {
        guard gesture.state == .began, let controller = Self.baselineController,
              controller.presentingViewController == nil,
              var presenter = Self.window?.rootViewController else { return }
        while let next = presenter.presentedViewController { presenter = next }
        Self.services?.reloadSnapshot()
        presenter.present(controller, animated: true)
    }
}
