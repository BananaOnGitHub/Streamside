import SwiftUI

// Observe only synthetic fixture renders; application callers leave this nil.
typealias PlayerMotionSample = (PlayerControlAnimation, PlayerControlRegion, Double, CGSize, PlayerControlFrame) -> Void
struct PlayerControlMotionEffect: AnimatableModifier {
    var progress: Double
    let style: PlayerControlAnimation
    let region: PlayerControlRegion
    let size: CGSize
    let glassEnabled: Bool
    var sample: PlayerMotionSample? = nil
    var animatableData: Double {
        get { progress }
        set { progress = newValue }
    }
    private func frame() -> PlayerControlFrame {
        let travel = PlayerControlMotion.travel(canvasWidth: Double(size.width), canvasHeight: Double(size.height))
        let value = PlayerControlMotion.frame(progress: progress, style: style, region: region,
                                             width: travel.width, height: travel.height)
        sample?(style, region, progress, CGSize(width: CGFloat(travel.width), height: CGFloat(travel.height)), value)
        return value
    }
    @ViewBuilder private func rendered(_ content: Content) -> some View {
        if #available(iOS 26.0, *), glassEnabled, region != .shade {
            // Contain glass extraction inside the region's alpha boundary.
            // An ancestor shared container can composite glass outside that boundary.
            GlassEffectContainer(spacing: 0) { content }
        } else { content }
    }
    func body(content: Content) -> some View {
        let value = frame()
        rendered(content)
            .compositingGroup()
            .opacity(value.opacity)
            .offset(x: CGFloat(value.x), y: CGFloat(value.y))
    }
}

// The info panel and the video overlay receive the same progress change in
// the same animation transaction. Measure the panel at its natural height.
struct PlayerInfoReveal: AnimatableModifier {
    var progress: Double
    let style: PlayerControlAnimation

    var animatableData: Double {
        get { progress }
        set { progress = newValue }
    }

    func body(content: Content) -> some View {
        let fraction = PlayerControlMotion.frame(progress: progress, style: style, region: .center,
                                                 width: 0, height: 0).opacity
        return PlayerInfoRevealLayout(fraction: CGFloat(fraction), slideContent: style != .fade) { content }
            .clipped()
            .opacity(style == .fade ? fraction : (fraction > 0 ? 1 : 0))
    }
}

private struct PlayerInfoRevealLayout: Layout {
    let fraction: CGFloat
    let slideContent: Bool

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        guard let content = subviews.first else { return .zero }
        let width = proposal.width.flatMap { $0.isFinite ? $0 : nil }
        let natural = content.sizeThatFits(ProposedViewSize(width: width, height: nil))
        return CGSize(width: natural.width, height: natural.height * fraction)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let point = CGPoint(x: bounds.minX, y: slideContent ? bounds.maxY : bounds.minY)
        subviews.first?.place(at: point, anchor: slideContent ? .bottomLeading : .topLeading,
                              proposal: ProposedViewSize(width: bounds.width, height: nil))
    }
}
