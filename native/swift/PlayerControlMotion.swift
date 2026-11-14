import SwiftUI

// Observe only synthetic fixture renders; application callers leave this nil.
typealias PlayerMotionSample = (PlayerControlAnimation, PlayerControlRegion, Double, PlayerControlFrame) -> Void
private struct PlayerRegionSize: PreferenceKey {
    static let defaultValue = CGSize.zero
    static func reduce(value: inout CGSize, nextValue: () -> CGSize) { value = nextValue() }
}
struct PlayerControlMotionEffect: AnimatableModifier {
    var progress: Double
    let style: PlayerControlAnimation
    let region: PlayerControlRegion
    let size: CGSize
    let glassEnabled: Bool
    var sample: PlayerMotionSample? = nil
    @State private var contentSize = CGSize.zero
    var animatableData: Double {
        get { progress }
        set { progress = newValue }
    }
    private func frame() -> PlayerControlFrame {
        // Travel only far enough to clear this region's nearest canvas edge.
        // A viewport-sized journey clips most of the easing curve offscreen.
        let width = contentSize.width > 0 ? min(size.width, contentSize.width + 16) : size.width
        let height = contentSize.height > 0 ? min(size.height, contentSize.height + 16) : size.height
        let value = PlayerControlMotion.frame(progress: progress, style: style, region: region,
                                             width: Double(width), height: Double(height))
        sample?(style, region, progress, value)
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
            .background(GeometryReader { geometry in
                Color.clear.preference(key: PlayerRegionSize.self, value: geometry.size)
            }.allowsHitTesting(false))
            .onPreferenceChange(PlayerRegionSize.self) { if contentSize != $0 { contentSize = $0 } }
            .compositingGroup()
            .opacity(value.opacity)
            .offset(x: CGFloat(value.x), y: CGFloat(value.y))
    }
}
