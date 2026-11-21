import SwiftUI
import UIKit

// Observe horizontal swipes on the profile without replacing its scroll view,
// text/link gestures, or the navigation controller's leading-edge back gesture.
struct ProfileTabSwipe: UIViewRepresentable {
    enum Event {
        case changed(CGFloat)
        case ended(CGFloat, velocity: CGFloat)
        case cancelled
    }

    let onPan: (Event) -> Void

    func makeUIView(context: Context) -> Anchor { Anchor() }

    func updateUIView(_ view: Anchor, context: Context) {
        view.onPan = onPan
    }

    final class Anchor: UIView, UIGestureRecognizerDelegate {
        var onPan: ((Event) -> Void)?
        private weak var target: UIView?
        private lazy var pan: UIPanGestureRecognizer = {
            let gesture = UIPanGestureRecognizer(target: self, action: #selector(panned(_:)))
            gesture.maximumNumberOfTouches = 1
            gesture.delegate = self
            return gesture
        }()

        override func didMoveToWindow() {
            super.didMoveToWindow()
            target?.removeGestureRecognizer(pan)
            target = nil
            guard window != nil else { return }
            var responder: UIResponder? = self
            while let current = responder {
                if let controller = current as? UIViewController {
                    let host = controller.view
                    host?.addGestureRecognizer(pan)
                    target = host
                    break
                }
                responder = current.next
            }
        }

        @objc private func panned(_ gesture: UIPanGestureRecognizer) {
            guard let target else { return }
            let distance = gesture.translation(in: target).x
            switch gesture.state {
            case .began, .changed: onPan?(.changed(distance))
            case .ended: onPan?(.ended(distance, velocity: gesture.velocity(in: target).x))
            case .cancelled, .failed: onPan?(.cancelled)
            default: break
            }
        }

        func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
            let velocity = pan.velocity(in: target)
            return abs(velocity.x) > 1.25 * abs(velocity.y)
        }

        func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
            guard let target else { return false }
            let x = touch.location(in: target).x
            guard x > 28, x < target.bounds.width - 28 else { return false }
            var ancestor = touch.view
            while let view = ancestor, view !== target {
                if view is UISegmentedControl { return false }
                if let scroll = view as? UIScrollView, scroll.isScrollEnabled,
                   scroll.contentSize.width > scroll.bounds.width + 1 { return false }
                ancestor = view.superview
            }
            return true
        }

        func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer,
                               shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer) -> Bool {
            otherGestureRecognizer is UIPanGestureRecognizer && !(otherGestureRecognizer is UIScreenEdgePanGestureRecognizer)
        }
    }
}

// Measure only the selected page so a taller offscreen About tab does not
// change the Home scroll range. Both pages use the same horizontal position.
struct ProfileTabPages: Layout {
    let selection: Int
    var position: CGFloat

    var animatableData: CGFloat {
        get { position }
        set { position = newValue }
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        guard subviews.indices.contains(selection) else { return .zero }
        let size = subviews[selection].sizeThatFits(ProposedViewSize(width: proposal.width, height: nil))
        return CGSize(width: proposal.width ?? size.width, height: size.height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        for index in subviews.indices {
            let x = bounds.minX + (CGFloat(index) - position) * bounds.width
            subviews[index].place(at: CGPoint(x: x, y: bounds.minY),
                                  anchor: .topLeading, proposal: ProposedViewSize(width: bounds.width, height: nil))
        }
    }
}
