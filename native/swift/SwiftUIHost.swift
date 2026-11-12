import SwiftUI
import UIKit

// Twitch retains its UIApplication/scene delegates, native bootstrap and window.
@objc(SSNSwiftUIHost)
@MainActor
public final class SSNSwiftUIHost: NSObject {
    private static var window: UIWindow?
    private static var services: NativeServices?
    private static var nativeController: UIViewController?
    private static var authenticationRoot: UIViewController?
    private static var authenticationController: UINavigationController?
    private static var diagnosticsController: UIViewController?
    private static var gestureTarget: SSNSwiftUIHost?
    private static var baseline = false

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
        let target = SSNSwiftUIHost()
        gestureTarget = target
        baseline = !native
        if native {
            retainAuthenticationRoot(window.rootViewController)
            let controller = UIHostingController(rootView: StreamsideShell(services: services))
            nativeController = controller
            if !SSNInstallWindowOwnership(window, controller) {
                // Keep diagnostics accessible; never claim guarded ownership.
                SSNNavigationEvent(3)
                services.actionUnavailable()
            }
        }
        let gesture = UILongPressGestureRecognizer(target: target, action: #selector(openDiagnostics(_:)))
        gesture.numberOfTouchesRequired = 2
        gesture.minimumPressDuration = 1
        gesture.cancelsTouchesInView = false
        gesture.delaysTouchesBegan = false
        gesture.delaysTouchesEnded = false
        window.addGestureRecognizer(gesture)
        SSNSwiftUIReady()
    }

    // UIKit containment only: no private getter, Swift layout, or controller
    // constructor is called. Do not load donor views to classify a proposed root.
    @objc(retainAuthenticationRoot:)
    public static func retainAuthenticationRoot(_ proposed: UIViewController?) {
        guard let proposed,
              let loginClass = NSClassFromString("_TtC6Twitch23LoggedOutViewController") else { return }
        var pending = [proposed]
        var visited = Set<ObjectIdentifier>()
        while let controller = pending.popLast(), visited.count < 64 {
            guard visited.insert(ObjectIdentifier(controller)).inserted else { continue }
            if controller.isKind(of: loginClass) {
                // Never replace/reparent an active authentication hierarchy.
                if authenticationController == nil { authenticationRoot = proposed }
                services?.canSignIn = authenticationRoot != nil
                return
            }
            pending.append(contentsOf: controller.children)
        }
    }

    public static func beginSignIn() -> Bool {
        guard SSNNavigationPermitted(), rootOwner() == 1,
              services?.state.session == .signedOut,
              authenticationController == nil,
              let root = nativeController, root.presentedViewController == nil,
              let donor = authenticationRoot, donor.parent == nil,
              donor.presentingViewController == nil,
              let target = gestureTarget else { return false }
        // This is Twitch's already-constructed welcome/login coordinator tree.
        // The owned navigation bar provides a way back without claiming to cancel
        // provider work, renew a token, or alter donor authentication state.
        let container = UINavigationController(rootViewController: donor)
        container.modalPresentationStyle = .fullScreen
        donor.navigationItem.leftBarButtonItem = UIBarButtonItem(
            title: "Close sign-in", style: .plain, target: target, action: #selector(closeSignIn))
        authenticationController = container
        authenticationRoot = nil
        services?.canSignIn = false
        SSNNavigationEvent(1)
        root.present(container, animated: true) { accountStateChanged() }
        return true
    }

    @objc public static func accountStateChanged() {
        services?.reloadSnapshot()
        guard let state = services?.state, authenticationController != nil,
              AuthenticationReturn.shouldReturn(session: state.session) else { return }
        finishAuthentication(verified: true)
    }

    private static func finishAuthentication(verified: Bool) {
        guard let controller = authenticationController,
              !controller.isBeingPresented, !controller.isBeingDismissed else { return }
        controller.dismiss(animated: true) {
            // Detach using UIKit's public containment API. Preserve the donor
            // login tree for another attempt while the account is signed out.
            let donor = controller.viewControllers.first
            controller.setViewControllers([], animated: false)
            authenticationController = nil
            authenticationRoot = donor
            services?.canSignIn = donor != nil
            SSNNavigationEvent(verified ? 2 : 4)
            services?.reloadSnapshot()
        }
    }

    @objc private func closeSignIn() { Self.finishAuthentication(verified: false) }

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
