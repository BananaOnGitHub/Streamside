import SwiftUI

// Persistent content avoids removal/lifetime and glass-material transitions.
// The frame values used here also allow the owned simulator fixture to observe
// actual interpolated modifier evaluations, without changing device diagnostics.
typealias PlayerMotionSample = (PlayerControlAnimation, PlayerControlRegion, Double, PlayerControlFrame) -> Void
struct PlayerControlMotionEffect: AnimatableModifier {
    var progress: Double
    let style: PlayerControlAnimation
    let region: PlayerControlRegion
    let size: CGSize
    var sample: PlayerMotionSample? = nil
    var animatableData: Double {
        get { progress }
        set { progress = newValue }
    }
    private func frame() -> PlayerControlFrame {
        let value = PlayerControlMotion.frame(progress: progress, style: style, region: region,
                                             width: Double(size.width), height: Double(size.height))
        sample?(style, region, progress, value)
        return value
    }
    func body(content: Content) -> some View {
        let value = frame()
        content.opacity(value.opacity).offset(x: CGFloat(value.x), y: CGFloat(value.y))
    }
}
