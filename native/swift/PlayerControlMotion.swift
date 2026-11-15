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
