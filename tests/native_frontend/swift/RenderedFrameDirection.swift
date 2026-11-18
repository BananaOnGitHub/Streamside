// Shared only by the Apple model and UI fixtures. SwiftUI can evaluate an
// identical animatable value repeatedly (including during glass extraction).
// Direction is between distinct values, not between repeated body evaluations.
struct RenderedFrameDirection {
    typealias Observation = (sequence: UInt64, style: PlayerControlAnimation, progress: Double, previous: Double)
    private(set) var latest: Observation?
    private var sequence: UInt64 = 0
    mutating func record(style: PlayerControlAnimation, progress: Double) {
        if let latest, latest.style == style, latest.progress == progress { return }
        let previous = latest.flatMap { $0.style == style ? $0.progress : nil } ?? progress
        sequence &+= 1
        latest = (sequence, style, progress, previous)
    }
}
