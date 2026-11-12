import SwiftUI

struct LiveRing: View {
    @ObservedObject var clock: StreamClock
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @AppStorage(FeedPreferences.livePingIndexKey) private var pingIndex = 2
    @State private var visible = false

    var body: some View {
        ZStack {
            Circle().stroke(.red, lineWidth: 1.5)
            if visible, !reduceMotion, clock.isActive, let cycle = LivePingCycle.seconds(index: pingIndex) {
                TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { context in
                    let progress = LivePingCycle.progress(at: context.date.timeIntervalSinceReferenceDate, cycle: cycle)
                    Circle().stroke(.red, lineWidth: 1.2)
                        .scaleEffect(1 + 0.5 * progress)
                        .opacity(0.55 * (1 - progress))
                }
            }
        }
        .onAppear { visible = true }
        .onDisappear { visible = false }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
