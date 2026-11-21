import UIKit

// The window owner stays mounted while UIKit pushes and pops a SwiftUI profile.
@MainActor final class ProfileNavigationController: UINavigationController, UINavigationControllerDelegate, UIGestureRecognizerDelegate {
    private(set) var profile: UIViewController?
    private var closing = false
    private var afterPop: (() -> Void)?

    init(root: UIViewController) {
        super.init(rootViewController: root)
        delegate = self
        setNavigationBarHidden(true, animated: false)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }

    override func viewDidLoad() {
        super.viewDidLoad()
        interactivePopGestureRecognizer?.delegate = self
    }

    func openProfile(_ controller: UIViewController) -> Bool {
        guard profile == nil, transitionCoordinator == nil, presentedViewController == nil else { return false }
        profile = controller
        pushViewController(controller, animated: true)
        return true
    }

    @discardableResult func closeProfile(completion: (() -> Void)? = nil) -> Bool {
        guard let profile, !closing else { return false }
        closing = true
        afterPop = completion
        if transitionCoordinator == nil, topViewController === profile {
            popViewController(animated: true)
        }
        return true
    }

    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        if gestureRecognizer !== interactivePopGestureRecognizer { return true }
        guard let profile else { return false }
        return topViewController === profile && !closing && transitionCoordinator == nil && presentedViewController == nil
    }

    func navigationController(_ navigationController: UINavigationController, didShow viewController: UIViewController, animated: Bool) {
        guard let profile else { return }
        if viewController === profile {
            // A close can arrive during a push or a cancelled edge swipe.
            if closing {
                DispatchQueue.main.async { [weak self] in
                    guard let self, self.topViewController === self.profile else { return }
                    self.popViewController(animated: true)
                }
            }
        } else if !viewControllers.contains(where: { $0 === profile }) {
            self.profile = nil
            closing = false
            let completion = afterPop
            afterPop = nil
            completion?()
        }
    }
}
