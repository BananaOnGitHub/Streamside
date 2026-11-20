import Combine
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

private struct PreviewActionTarget: UIViewRepresentable {
    let title: String
    let identifier: String
    let action: (() -> Void)?

    @MainActor final class Coordinator: NSObject {
        var action: (() -> Void)?
        @objc func activate() { action?() }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> UIButton {
        let button = UIButton(type: .custom)
        button.isAccessibilityElement = true
        button.addTarget(context.coordinator, action: #selector(Coordinator.activate), for: .touchUpInside)
        return button
    }

    func updateUIView(_ button: UIButton, context: Context) {
        context.coordinator.action = action
        button.isEnabled = action != nil
        button.accessibilityLabel = title
        button.accessibilityIdentifier = identifier
    }
}

private struct PreviewActions: View {
    let watch: () -> Void
    let profile: (() -> Void)?
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    private func row(_ title: String, icon: String, identifier: String, action: (() -> Void)?) -> some View {
        Label(title, systemImage: icon)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 20).padding(.vertical, 15)
            .opacity(action == nil ? 0.4 : 1)
            .allowsHitTesting(false).accessibilityHidden(true)
            .overlay { PreviewActionTarget(title: title, identifier: identifier, action: action) }
    }

    private var rows: some View {
        VStack(spacing: 0) {
            row("Watch stream", icon: "play.fill", identifier: "quicklook.watch", action: watch)
            Divider().padding(.horizontal, 16)
            row("View profile", icon: "person.fill", identifier: "quicklook.profile", action: profile)
        }.font(.body).foregroundStyle(.primary)
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
final class AnchoredPreviewController: UIViewController, UIGestureRecognizerDelegate {
    private let content: UIViewController
    private weak var source: UIView?
    private let initialLift: UIView?
    private let onWatch: () -> Void
    private let onDismiss: () -> Void
    private let onProfile: (() -> Void)?
    private let videoTapAvailability: AnyPublisher<Bool, Never>?
    private var videoTapObservation: AnyCancellable?
    private let observeTarget: ((Bool, CGRect, CGPoint) -> Void)?
    private var actions: UIViewController?
    private let backdrop = UIControl()
    private let card = UIView()
    private var lifted: UIView?
    private var sourceFrame = CGRect.zero
    private var sourceWasHidden = false
    private var sourceRestored = false
    private var returnStage: UIView?
    private var returnLink: CADisplayLink?
    private var returnStarted: CFTimeInterval = 0
    private var returnDuration: TimeInterval = 0
    private var animator: UIViewPropertyAnimator?
    private var closing = false
    private var installed = false
    private var appeared = false
    private lazy var swipe = UIPanGestureRecognizer(target: self, action: #selector(dragPreview(_:)))
    private weak var touchedScroll: UIScrollView?
    private var dragging = false
    private var dragStart = CGPoint.zero
    private var menuStart = CGPoint.zero

    init(content: UIViewController, source: UIView, watch: @escaping () -> Void, dismiss: @escaping () -> Void,
         observeTarget: ((Bool, CGRect, CGPoint) -> Void)?, initialLift: UIView? = nil, videoTapAvailability: AnyPublisher<Bool, Never>? = nil, profile: (() -> Void)? = nil) {
        onProfile = profile
        self.videoTapAvailability = videoTapAvailability
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
        let actions = UIHostingController(rootView: PreviewActions(watch: { [weak self] in self?.onWatch() }, profile: onProfile))
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
        // Remove the Watch overlay from both UIKit hit testing and accessibility
        // while consent owns the slot. Overriding point(inside:) alone leaves
        // an overlapping accessibility button above SwiftUI's warning controls.
        // The main-actor @Published gate delivers its current value immediately,
        // then restores Watch only after final consent, without a polling timer.
        videoTapObservation = videoTapAvailability?.removeDuplicates().sink { [weak watch] enabled in
            watch?.isHidden = !enabled
            watch?.isUserInteractionEnabled = enabled
            watch?.isAccessibilityElement = enabled
            watch?.accessibilityElementsHidden = !enabled
        }
        content.view.addSubview(watch)
        actions.view.frame = placement.menu
        actions.view.layer.shadowColor = UIColor.black.cgColor; actions.view.layer.shadowOpacity = 0.15
        actions.view.layer.shadowRadius = 14; actions.view.layer.shadowOffset = CGSize(width: 0, height: 6)
        view.layoutIfNeeded()
        swipe.delegate = self; view.addGestureRecognizer(swipe)
        // Let our direction/edge admission decide first; vertical content
        // scrolling wins unless it is already at its outward boundary.
        var pending: [UIView] = [content.view]
        var count = 0
        while let item = pending.popLast(), count < 256 {
            count += 1; pending.append(contentsOf: item.subviews)
            if let scroll = item as? UIScrollView { scroll.panGestureRecognizer.require(toFail: swipe) }
        }
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
        closing = true; dragging = false
        if !watching {
            // Closing becomes a passive visual immediately. A new feed touch
            // must not wait for the return animation or its media transaction.
            view.isUserInteractionEnabled = false
            view.accessibilityViewIsModal = false; view.accessibilityElementsHidden = true
            restoreSource()
        }
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
        if !watching && UIApplication.shared.applicationState == .active, let lifted, lifted.superview == nil {
            lifted.frame = content.view.convert(CGRect(x: 0, y: 0, width: card.bounds.width, height: card.bounds.width * 9 / 16), to: view)
            lifted.alpha = 1; view.addSubview(lifted)
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
        animation.addCompletion { [self] _ in
            detach(restoreFocus: !watching); completion()
        }
        if returning { beginReturnTracking(duration: duration) }
        animator = animation; animation.startAnimation()
    }
    private func restoreSource() {
        guard installed, !sourceRestored else { return }
        source?.isHidden = sourceWasHidden; sourceRestored = true
    }
    private func beginReturnTracking(duration: TimeInterval) {
        // Keep the accepted spring and its fixed deadline. Only translate its
        // coordinate space as the row moves; never retarget/restart the spring.
        let stage = UIView(frame: view.bounds); stage.isUserInteractionEnabled = false
        view.addSubview(stage); stage.addSubview(card)
        if let lifted, lifted.superview === view { stage.addSubview(lifted) }
        returnStage = stage; returnDuration = duration; returnStarted = CACurrentMediaTime()
        let link = CADisplayLink(target: self, selector: #selector(trackReturningSource(_:)))
        returnLink = link; link.add(to: .main, forMode: .common)
    }
    @objc private func trackReturningSource(_ link: CADisplayLink) {
        guard let stage = returnStage, let source, source.window === view.window else { return }
        let current = source.convert(source.bounds, to: view)
        let elapsed = max(0, CACurrentMediaTime() - returnStarted)
        let progress = min(1, CGFloat(elapsed / max(0.001, returnDuration)))
        let weight = 1 - pow(1 - progress, 3)
        stage.transform = CGAffineTransform(translationX: (current.midX - sourceFrame.midX) * weight,
            y: (current.midY - sourceFrame.midY) * weight)
        // UIViewPropertyAnimator owns completion at the original deadline. A
        // source disappearing or continuous scrolling cannot prolong cleanup.
    }
    private func stopReturnTracking() {
        returnLink?.invalidate(); returnLink = nil; returnStage = nil
    }
    private func detach(restoreFocus: Bool = false) {
        videoTapObservation?.cancel(); videoTapObservation = nil
        stopReturnTracking()
        if appeared { beginAppearanceTransition(false, animated: false) }
        restoreSource(); installed = false
        animator = nil
        willMove(toParent: nil); view.removeFromSuperview(); removeFromParent()
        if appeared { endAppearanceTransition(); appeared = false }
        if restoreFocus && source?.isHidden == false && UIAccessibility.isVoiceOverRunning { UIAccessibility.post(notification: .screenChanged, argument: source) }
    }
    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        guard !closing else { return false }
        let point = touch.location(in: view)
        guard card.frame.contains(point) else { return false }
        touchedScroll = nil
        var item = touch.view
        while let current = item, current !== view {
            if let scroll = current as? UIScrollView { touchedScroll = scroll; break }
            item = current.superview
        }
        return true
    }
    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard !closing, installed, animator == nil else { return false }
        let velocity = swipe.velocity(in: view)
        if abs(velocity.y) > abs(velocity.x), let scroll = touchedScroll,
           scroll.contentSize.height > scroll.bounds.height + 1 {
            let top = -scroll.adjustedContentInset.top
            let bottom = max(top, scroll.contentSize.height - scroll.bounds.height + scroll.adjustedContentInset.bottom)
            if (velocity.y > 0 && scroll.contentOffset.y > top + 1) ||
               (velocity.y < 0 && scroll.contentOffset.y < bottom - 1) { return false }
        }
        return true
    }
    @objc private func dragPreview(_ gesture: UIPanGestureRecognizer) {
        guard !closing else { return }
        let translation = gesture.translation(in: view)
        switch gesture.state {
        case .began:
            dragging = true
            dragStart = card.center; menuStart = actions?.view.center ?? .zero
            fallthrough
        case .changed:
            guard dragging else { return }
            card.center = CGPoint(x: dragStart.x + translation.x, y: dragStart.y + translation.y)
            actions?.view.center = CGPoint(x: menuStart.x + translation.x, y: menuStart.y + translation.y)
            backdrop.alpha = max(0.6, 1 - hypot(translation.x, translation.y) / 500)
        case .ended:
            guard dragging else { return }
            let velocity = gesture.velocity(in: view)
            if hypot(translation.x, translation.y) >= 55 ||
               (hypot(translation.x, translation.y) >= 12 && hypot(velocity.x, velocity.y) >= 700) {
                onDismiss()
            } else { settleDrag() }
        case .cancelled, .failed: if dragging { settleDrag() }
        default: break
        }
    }
    private func settleDrag() {
        guard !closing else { return }
        dragging = false
        let animation = UIViewPropertyAnimator(duration: UIAccessibility.isReduceMotionEnabled ? 0.15 : 0.3, dampingRatio: 1) {
            self.card.center = self.dragStart; self.actions?.view.center = self.menuStart; self.backdrop.alpha = 1
        }
        animation.addCompletion { [weak self] _ in self?.animator = nil }
        animator = animation; animation.startAnimation()
    }
    @objc private func outside() { onDismiss() }
    @objc private func watchPreview() { onWatch() }
    override func accessibilityPerformEscape() -> Bool { onDismiss(); return true }
    override func viewWillTransition(to size: CGSize, with coordinator: UIViewControllerTransitionCoordinator) {
        super.viewWillTransition(to: size, with: coordinator); onDismiss()
    }
}
