import UIKit

// A preview-provider controller, never presented by Streamside as a modal.
// Mask the media subtree at the UIKit boundary as well as in SwiftUI.
@MainActor
final class QuickLookController: UIViewController {
    let content: UIViewController
    init(content: UIViewController, size: CGSize) {
        self.content = content
        super.init(nibName: nil, bundle: nil)
        preferredContentSize = size
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .clear
        content.view.backgroundColor = .clear
        view.layer.cornerRadius = 24; view.layer.cornerCurve = .continuous
        view.layer.masksToBounds = true
        addChild(content)
        content.view.frame = view.bounds
        content.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(content.view); content.didMove(toParent: self)
    }
}
