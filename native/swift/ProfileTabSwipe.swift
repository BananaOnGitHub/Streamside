import SwiftUI
import UIKit

// Observe horizontal swipes on the profile without replacing its scroll view,
// text/link gestures, or the navigation controller's leading-edge back gesture.
struct ProfileTabSwipe: UIViewRepresentable {
    @Binding var selection: Int

    func makeUIView(context: Context) -> Anchor { Anchor() }

    func updateUIView(_ view: Anchor, context: Context) {
        view.select = { page in selection = page }
    }

    final class Anchor: UIView, UIGestureRecognizerDelegate {
        var select: ((Int) -> Void)?
        private weak var target: UIView?
        private lazy var left = makeSwipe(.left)
        private lazy var right = makeSwipe(.right)

        override func didMoveToWindow() {
            super.didMoveToWindow()
            target?.removeGestureRecognizer(left)
            target?.removeGestureRecognizer(right)
            target = nil
            guard window != nil else { return }
            var responder: UIResponder? = self
            while let current = responder {
                if let controller = current as? UIViewController {
                    let host = controller.view
                    host?.addGestureRecognizer(left)
                    host?.addGestureRecognizer(right)
                    target = host
                    break
                }
                responder = current.next
            }
        }

        private func makeSwipe(_ direction: UISwipeGestureRecognizer.Direction) -> UISwipeGestureRecognizer {
            let gesture = UISwipeGestureRecognizer(target: self, action: #selector(swiped(_:)))
            gesture.direction = direction
            gesture.cancelsTouchesInView = false
            gesture.delegate = self
            return gesture
        }

        @objc private func swiped(_ gesture: UISwipeGestureRecognizer) {
            let leftToRight = effectiveUserInterfaceLayoutDirection == .leftToRight
            select?((gesture.direction == .left) == leftToRight ? 1 : 0)
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
