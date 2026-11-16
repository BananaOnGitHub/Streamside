import UIKit

// Owned containment keeps Twitch's guarded window root intact. Watch replaces
// the preview child in this same presentation; there is no second modal slide.
@MainActor
final class QuickLookController: UIViewController {
    private var preview: UIViewController?
    private let makeTheatre: () -> UIViewController
    private let start: () -> Void
    private let watched: () -> Void
    private let stop: () -> Void
    private var started = false
    private var closed = false
    private(set) var watching = false
    private(set) var transitioning = false
    var fadeDuration: TimeInterval { UIAccessibility.isReduceMotionEnabled ? 0.2 : 0.35 }

    init(preview: UIViewController, makeTheatre: @escaping () -> UIViewController,
         start: @escaping () -> Void, watched: @escaping () -> Void, stop: @escaping () -> Void) {
        self.preview = preview; self.makeTheatre = makeTheatre
        self.start = start; self.watched = watched; self.stop = stop
        super.init(nibName: nil, bundle: nil)
        modalPresentationStyle = .overFullScreen
        modalTransitionStyle = .crossDissolve
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
    override var supportedInterfaceOrientations: UIInterfaceOrientationMask { .portrait }
    override var preferredInterfaceOrientationForPresentation: UIInterfaceOrientation { .portrait }
    override var shouldAutorotate: Bool { false }
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .clear
        if let preview { install(preview) }
    }
    private func install(_ child: UIViewController) {
        addChild(child)
        child.view.frame = view.bounds
        child.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(child.view)
        child.didMove(toParent: self)
    }
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        if !started && !closed { started = true; start() }
        setNeedsUpdateOfSupportedInterfaceOrientations()
        view.window?.windowScene?.requestGeometryUpdate(.iOS(interfaceOrientations: .portrait))
    }
    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        if isBeingDismissed { finish() }
    }
    private func finish() {
        guard !closed else { return }
        closed = true; stop()
    }
    // Also stops if a parent removes this controller without normal dismissal.
    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        if presentingViewController == nil { finish() }
    }
    func watch() {
        guard !closed, !watching, !transitioning, let preview else { return }
        watching = true; transitioning = true
        view.isUserInteractionEnabled = false
        // Keep the actual preview hierarchy through the fade. Its media surface
        // is reparented into the theatre, so only one IVS player/request exists.
        let theatre = makeTheatre()
        install(theatre)
        theatre.view.alpha = 0
        view.bringSubviewToFront(preview.view)
        UIView.animate(withDuration: fadeDuration, delay: 0,
                       options: [.curveEaseOut, .beginFromCurrentState]) {
            theatre.view.alpha = 1
            preview.view.alpha = 0
        } completion: { [weak self] _ in
            guard let self else { return }
            preview.willMove(toParent: nil)
            preview.view.removeFromSuperview(); preview.removeFromParent()
            self.preview = nil; self.transitioning = false
            self.view.isUserInteractionEnabled = true
            if !self.closed { self.watched() }
        }
    }
}
