import SwiftUI
import UIKit

// The media view is display-only. It must never participate in input routing,
// including when its internal video/ad renderer changes size or adds subviews.
private struct PassivePlayerSurface: UIViewRepresentable {
    let surface: UIView
    func makeUIView(context: Context) -> UIView {
        let container = UIView()
        container.backgroundColor = .black
        container.clipsToBounds = true
        container.isUserInteractionEnabled = false
        surface.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(surface)
        NSLayoutConstraint.activate([
            surface.leadingAnchor.constraint(equalTo: container.leadingAnchor),
            surface.trailingAnchor.constraint(equalTo: container.trailingAnchor),
            surface.topAnchor.constraint(equalTo: container.topAnchor),
            surface.bottomAnchor.constraint(equalTo: container.bottomAnchor)
        ])
        return container
    }
    func updateUIView(_ view: UIView, context: Context) {}
    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UIView, context: Context) -> CGSize? {
        guard let width = proposal.width, let height = proposal.height else { return nil }
        return CGSize(width: width, height: height)
    }
}

struct PlayerCanvas<Controls: View>: View {
    let surface: UIView
    let toggleControls: () -> Void
    let controls: () -> Controls
    init(surface: UIView, toggleControls: @escaping () -> Void, @ViewBuilder controls: @escaping () -> Controls) {
        self.surface = surface; self.toggleControls = toggleControls; self.controls = controls
    }
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                PassivePlayerSurface(surface: surface).allowsHitTesting(false)
                // Sibling of the controls, not an ancestor gesture attached to
                // the representable/overlay. Only unoccupied video space taps it.
                Color.clear.contentShape(Rectangle())
                    .onTapGesture(perform: toggleControls)
                    .accessibilityLabel("Show or hide player controls")
                    .accessibilityIdentifier("player.video")
                    .accessibilityAddTraits(.isButton)
                controls()
            }
            .frame(width: geometry.size.width, height: geometry.size.height)
            .clipped()
        }
        .aspectRatio(16.0 / 9.0, contentMode: .fit)
    }
}
