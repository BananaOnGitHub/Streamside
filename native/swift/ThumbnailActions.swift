import SwiftUI
import UIKit

// A successful hold must consume the following release, while an ordinary tap
// still watches. UIScrollView can cancel the recognizers when a drag wins.
struct ThumbnailActions: UIViewRepresentable {
    let open: () -> Void
    let preview: () -> Void
    final class Coordinator: NSObject {
        var owner: ThumbnailActions
        init(_ owner: ThumbnailActions) { self.owner = owner }
        @objc func tap(_ gesture: UITapGestureRecognizer) {
            if gesture.state == .ended { owner.open() }
        }
        @objc func hold(_ gesture: UILongPressGestureRecognizer) {
            if gesture.state == .began { owner.preview() }
        }
    }
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeUIView(context: Context) -> UIView {
        let view = UIView()
        let hold = UILongPressGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.hold(_:)))
        hold.minimumPressDuration = 0.5
        hold.allowableMovement = 10
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.tap(_:)))
        tap.require(toFail: hold)
        view.addGestureRecognizer(hold); view.addGestureRecognizer(tap)
        view.isAccessibilityElement = false
        return view
    }
    func updateUIView(_ view: UIView, context: Context) { context.coordinator.owner = self }
}
