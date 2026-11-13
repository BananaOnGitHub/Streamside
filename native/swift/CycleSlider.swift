import SwiftUI
import UIKit

@MainActor
private final class CycleSliderFeedback: ObservableObject {
    private let selection = UISelectionFeedbackGenerator()
    func prepare() { selection.prepare() }
    func changed() { selection.selectionChanged(); selection.prepare() }
}

// Own the seven-stop track instead of delegating feedback to the system's
// stepped Slider. There is one explicit feedback call per accepted detent change.
struct CycleSlider: View {
    @Binding var index: Int
    @Environment(\.isEnabled) private var enabled
    @Environment(\.layoutDirection) private var direction
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @State private var selection = CycleDetentSelection(index: 2)
    @State private var dragging = false
    @StateObject private var feedback = CycleSliderFeedback()

    init(index: Binding<Int>) {
        _index = index
        _selection = State(initialValue: CycleDetentSelection(index: index.wrappedValue))
    }

    var body: some View {
        GeometryReader { geometry in
            let travel = max(0, geometry.size.width - 28)
            let fraction = CGFloat(selection.index) / 6
            let rtl = direction == .rightToLeft
            let physicalFraction = rtl ? 1 - fraction : fraction
            let fill = travel * fraction
            ZStack {
                Capsule().fill(Color.secondary.opacity(0.25))
                    .frame(width: travel, height: 4)
                    .position(x: geometry.size.width / 2, y: 22)
                Capsule().fill(Color.accentColor)
                    .frame(width: fill, height: 4)
                    .position(x: rtl ? geometry.size.width - 14 - fill / 2 : 14 + fill / 2, y: 22)
                thumb
                    .position(x: 14 + travel * physicalFraction, y: 22)
            }
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0).onChanged { value in
                guard enabled, travel > 0 else { return }
                if !dragging {
                    dragging = true
                    selection = CycleDetentSelection(index: index)
                    feedback.prepare()
                }
                let physical = (value.location.x - 14) / travel
                let position = (rtl ? 1 - physical : physical) * 6
                if selection.move(to: Double(position)) { commitSelection() }
            }.onEnded { _ in dragging = false }, including: enabled ? .all : .none)
        }
        .frame(height: 44)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Live ring cycle")
        .accessibilityValue(LivePingCycle.label(index: index))
        .accessibilityAdjustableAction { action in
            guard enabled else { return }
            selection = CycleDetentSelection(index: index)
            switch action {
            case .increment:
                if selection.step(increasing: true) { commitSelection() }
            case .decrement:
                if selection.step(increasing: false) { commitSelection() }
            @unknown default: break
            }
        }
        .onAppear { selection = CycleDetentSelection(index: index) }
        .onChange(of: index) { value in selection = CycleDetentSelection(index: value) }
        .onChange(of: enabled) { value in if !value { dragging = false } }
    }
    @ViewBuilder private var thumb: some View {
        if #available(iOS 26.0, *), !reduceTransparency {
            Circle().fill(.clear).frame(width: 28, height: 28)
                .glassEffect(.regular.interactive(), in: Circle())
        } else {
            Circle().fill(.white)
                .overlay(Circle().stroke(Color.secondary.opacity(0.3), lineWidth: 0.5))
                .shadow(color: .black.opacity(0.2), radius: 2, y: 1)
                .frame(width: 28, height: 28)
        }
    }
    private func commitSelection() {
        // Also protect against an external preference update during a gesture.
        guard selection.index != LivePingCycle.normalized(index) else { return }
        index = selection.index
        feedback.changed()
    }
}
