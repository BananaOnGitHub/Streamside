import SwiftUI
import UIKit

// The system context-preview prototype cannot scroll its information subtree.
// This child controller keeps that subtree interactive and never presents a modal.
struct PreviewPlacement {
    let card: CGRect
    let menu: CGRect
    @MainActor static func viewport(in view: UIView) -> CGRect {
        let safe = view.safeAreaInsets
        return view.bounds.inset(by: UIEdgeInsets(top: safe.top + 12, left: safe.left + 16,
            bottom: safe.bottom + 16, right: safe.right + 16))
    }
    static func holdTarget(source: CGRect) -> CGRect {
        // Subtle, centered enlargement; only the admitted preview travels.
        source.insetBy(dx: -source.width * 0.025, dy: -source.height * 0.025)
    }
    static func collapsedCenter(source: CGRect, card: CGSize) -> CGPoint {
        let scale = source.width / max(1, card.width)
        return CGPoint(x: source.midX, y: source.minY + card.height * scale / 2)
    }
    static func make(viewport: CGRect, source: CGRect, card: CGSize, menu: CGSize) -> PreviewPlacement? {
        let gap: CGFloat = 14
        let height = min(card.height, viewport.height - menu.height - gap)
        guard card.width > 0, card.width <= viewport.width, menu.width > 0, menu.width <= viewport.width,
              menu.height > 0, height >= card.width * 9 / 16 + 44 else { return nil }
        let total = height + gap + menu.height
        let top = min(max(source.midY - height / 2, viewport.minY), viewport.maxY - total)
        return PreviewPlacement(card: CGRect(x: viewport.midX - card.width / 2, y: top, width: card.width, height: height),
            menu: CGRect(x: viewport.midX - menu.width / 2, y: top + height + gap, width: menu.width, height: menu.height))
    }
}

private struct PreviewActions: View {
    let watch: () -> Void
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    private var rows: some View {
        VStack(spacing: 0) {
            Button(action: watch) {
                Label("Watch stream", systemImage: "play.fill")
                    .frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 20).padding(.vertical, 15)
                    .contentShape(Rectangle())
            }.accessibilityIdentifier("quicklook.watch")
            Divider().padding(.horizontal, 16)
            Button {} label: {
                Label("View profile", systemImage: "person.fill")
                    .frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 20).padding(.vertical, 15)
            }.disabled(true).opacity(0.4).accessibilityHint("Not available yet")
        }.font(.body).foregroundStyle(.primary).buttonStyle(.plain)
    }
    var body: some View {
        let shape = RoundedRectangle(cornerRadius: 24, style: .continuous)
        Group {
            if reduceTransparency { rows.background(Color(uiColor: .secondarySystemBackground), in: shape) }
            else if #available(iOS 26.0, *) { rows.glassEffect(.regular, in: shape) }
            else { rows.background(.regularMaterial, in: shape) }
        }
        .clipShape(shape).accessibilityElement(children: .contain).accessibilityIdentifier("quicklook.menu")
    }
}

@MainActor
final class AnchoredPreviewController: UIViewController {
    private let content: UIViewController
    private weak var source: UIView?
    private let initialLift: UIView?
    private let onWatch: () -> Void
    private let onDismiss: () -> Void
    private let observeTarget: ((Bool, CGRect, CGPoint) -> Void)?
    private var actions: UIViewController?
    private let backdrop = UIControl()
    private let card = UIView()
    private var lifted: UIView?
    private var sourceFrame = CGRect.zero
    private var sourceWasHidden = false
    private var animator: UIViewPropertyAnimator?
    private var closing = false
    private var installed = false
    private var appeared = false

    init(content: UIViewController, source: UIView, watch: @escaping () -> Void, dismiss: @escaping () -> Void,
         observeTarget: ((Bool, CGRect, CGPoint) -> Void)?, initialLift: UIView? = nil) {
        self.initialLift = initialLift
        self.content = content; self.source = source; onWatch = watch; onDismiss = dismiss; self.observeTarget = observeTarget
        super.init(nibName: nil, bundle: nil)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .clear; view.isOpaque = false; view.accessibilityViewIsModal = true
        backdrop.frame = view.bounds; backdrop.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        if UIAccessibility.isReduceTransparencyEnabled { backdrop.backgroundColor = .black.withAlphaComponent(0.7) }
        else {
            let blur = UIVisualEffectView(effect: UIBlurEffect(style: .systemChromeMaterial))
            blur.frame = backdrop.bounds; blur.autoresizingMask = [.flexibleWidth, .flexibleHeight]; blur.isUserInteractionEnabled = false
            backdrop.addSubview(blur); backdrop.backgroundColor = .black.withAlphaComponent(0.12)
        }
        backdrop.addTarget(self, action: #selector(outside), for: .touchUpInside)
        backdrop.isAccessibilityElement = true
        backdrop.accessibilityLabel = "Dismiss stream preview"; backdrop.accessibilityTraits = .button
        view.addSubview(backdrop)
        card.layer.shadowColor = UIColor.black.cgColor; card.layer.shadowOpacity = 0.22
        card.layer.shadowRadius = 18; card.layer.shadowOffset = CGSize(width: 0, height: 8)
        view.addSubview(card)
        addChild(content); card.addSubview(content.view); content.didMove(toParent: self)
        let actions = UIHostingController(rootView: PreviewActions(watch: { [weak self] in self?.onWatch() }))
        actions.view.backgroundColor = .clear; actions.view.isOpaque = false
        addChild(actions); view.addSubview(actions.view); actions.didMove(toParent: self); self.actions = actions
    }
    @discardableResult func install(in root: UIViewController) -> Bool {
        guard let source, source.window === root.view.window, root.presentedViewController == nil else { return false }
        root.addChild(self); view.frame = root.view.bounds; view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        beginAppearanceTransition(true, animated: false)
        root.view.addSubview(view); didMove(toParent: root)
        endAppearanceTransition(); appeared = true; view.layoutIfNeeded()
        sourceFrame = source.convert(source.bounds, to: view)
        let viewport = PreviewPlacement.viewport(in: view)
        let width = content.preferredContentSize.width
        let menuWidth = traitCollection.preferredContentSizeCategory.isAccessibilityCategory ? width : min(280, width * 0.75)
        guard let actions = actions as? UIHostingController<PreviewActions>,
              let placement = PreviewPlacement.make(viewport: viewport, source: sourceFrame, card: content.preferredContentSize,
                menu: CGSize(width: menuWidth, height: ceil(actions.sizeThatFits(in: CGSize(width: menuWidth, height: 1000)).height))) else {
            detach(); return false
        }
        card.frame = placement.card; content.view.frame = card.bounds
        content.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        card.layer.shadowPath = UIBezierPath(roundedRect: card.bounds, cornerRadius: 24).cgPath
        let watch = UIButton(type: .custom)
        watch.frame = CGRect(x: 0, y: 0, width: card.bounds.width, height: card.bounds.width * 9 / 16)
        watch.accessibilityLabel = "Watch stream preview"; watch.accessibilityIdentifier = "quicklook.play-preview"
        watch.addTarget(self, action: #selector(watchPreview), for: .touchUpInside)
        content.view.addSubview(watch)
        actions.view.frame = placement.menu
        actions.view.layer.shadowColor = UIColor.black.cgColor; actions.view.layer.shadowOpacity = 0.15
        actions.view.layer.shadowRadius = 14; actions.view.layer.shadowOffset = CGSize(width: 0, height: 6)
        view.layoutIfNeeded()
        let liftFrame = initialLift.map { view.convert($0.frame, from: source.window) } ?? sourceFrame
        lifted = initialLift ?? source.snapshotView(afterScreenUpdates: false)
        if let lifted {
            lifted.frame = liftFrame; lifted.isUserInteractionEnabled = false
            lifted.layer.cornerCurve = .continuous; lifted.layer.cornerRadius = 7; lifted.layer.masksToBounds = true
            view.addSubview(lifted)
        }
        sourceWasHidden = source.isHidden; source.isHidden = true; installed = true
        let windowRect = source.convert(source.bounds, to: source.window)
        observeTarget?(false, windowRect, CGPoint(x: windowRect.midX, y: windowRect.midY))
        let destination = card.center
        let scale = liftFrame.width / card.bounds.width
        card.center = PreviewPlacement.collapsedCenter(source: liftFrame, card: card.bounds.size)
        card.transform = CGAffineTransform(scaleX: scale, y: scale); card.alpha = 0
        actions.view.alpha = 0; actions.view.transform = CGAffineTransform(translationX: 0, y: 8); backdrop.alpha = 0
        if UIAccessibility.isReduceMotionEnabled {
            card.transform = .identity; card.center = destination; actions.view.transform = .identity; lifted?.alpha = 0
        }
        let animation = UIViewPropertyAnimator(duration: UIAccessibility.isReduceMotionEnabled ? 0.2 : 0.46, dampingRatio: 0.88)
        animation.addAnimations {
            self.backdrop.alpha = 1; self.card.center = destination; self.card.transform = .identity
            self.actions?.view.alpha = 1; self.actions?.view.transform = .identity
            self.lifted?.frame = CGRect(x: placement.card.minX, y: placement.card.minY, width: placement.card.width, height: placement.card.width * 9 / 16)
            self.lifted?.layer.cornerRadius = 24
        }
        animation.addAnimations({ self.card.alpha = 1; self.lifted?.alpha = 0 }, delayFactor: 0.15)
        animation.addCompletion { [weak self] _ in
            guard let self, !self.closing else { return }
            self.lifted?.removeFromSuperview(); self.animator = nil
            UIAccessibility.post(notification: .screenChanged, argument: self.content.view)
        }
        animator = animation; animation.startAnimation(); return true
    }
    func dismiss(watching: Bool, completion: @escaping () -> Void) {
        guard !closing else { return }
        closing = true
        guard installed || parent != nil else { completion(); return }
        // Preserve interpolated geometry when a lifecycle event interrupts entry.
        if let animator {
            animator.pauseAnimation()
            let items: [UIView?] = [card, actions?.view, lifted, backdrop]
            for item in items.compactMap({ $0 }) {
                if let shown = item.layer.presentation() {
                    item.bounds = shown.bounds; item.center = shown.position
                    item.transform = CATransform3DGetAffineTransform(shown.transform)
                    item.alpha = CGFloat(shown.opacity)
                }
            }
            animator.stopAnimation(true); self.animator = nil
        }
        if let source, source.window != nil {
            sourceFrame = source.convert(source.bounds, to: view)
            let rect = source.convert(source.bounds, to: source.window)
            observeTarget?(true, rect, CGPoint(x: rect.midX, y: rect.midY))
        }
        let moving = !UIAccessibility.isReduceMotionEnabled && UIApplication.shared.applicationState == .active
        if moving && !watching, let lifted, lifted.superview == nil {
            lifted.frame = content.view.convert(CGRect(x: 0, y: 0, width: card.bounds.width, height: card.bounds.width * 9 / 16), to: view)
            lifted.alpha = 0; view.addSubview(lifted)
        }
        // A critically damped spring sheds velocity as it reaches the source,
        // without an overshoot or a constant-speed final segment. Watch remains
        // a fade; only the spatial return gets the longer settling motion.
        let returning = moving && !watching
        let duration = UIApplication.shared.applicationState == .active ? (returning ? 0.52 : 0.18) : 0
        let animation = returning
            ? UIViewPropertyAnimator(duration: duration, dampingRatio: 1)
            : UIViewPropertyAnimator(duration: duration, curve: .easeInOut)
        animation.addAnimations {
            self.backdrop.alpha = 0; self.actions?.view.alpha = 0; self.card.alpha = 0; self.lifted?.alpha = 0
            if moving && !watching {
                self.card.center = PreviewPlacement.collapsedCenter(source: self.sourceFrame, card: self.card.bounds.size)
                self.lifted?.frame = self.sourceFrame; self.lifted?.layer.cornerRadius = 7; self.lifted?.alpha = 1
                let scale = self.sourceFrame.width / max(1, self.card.bounds.width)
                self.card.transform = CGAffineTransform(scaleX: scale, y: scale)
            }
        }
        animation.addCompletion { [self] _ in detach(restoreFocus: !watching); completion() }
        animator = animation; animation.startAnimation()
    }
    private func detach(restoreFocus: Bool = false) {
        if appeared { beginAppearanceTransition(false, animated: false) }
        if installed { source?.isHidden = sourceWasHidden; installed = false }
        animator = nil
        willMove(toParent: nil); view.removeFromSuperview(); removeFromParent()
        if appeared { endAppearanceTransition(); appeared = false }
        if restoreFocus && UIAccessibility.isVoiceOverRunning { UIAccessibility.post(notification: .screenChanged, argument: source) }
    }
    @objc private func outside() { onDismiss() }
    @objc private func watchPreview() { onWatch() }
    override func accessibilityPerformEscape() -> Bool { onDismiss(); return true }
    override func viewWillTransition(to size: CGSize, with coordinator: UIViewControllerTransitionCoordinator) {
        super.viewWillTransition(to: size, with: coordinator); onDismiss()
    }
}
