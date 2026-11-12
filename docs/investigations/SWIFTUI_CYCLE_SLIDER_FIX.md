# Cycle slider endpoint feedback correction

Starts from clean feat/native-frontend at c72c5ae, compiled source
94d2ee3bab41f209a4948d45e3ea35cd700e7329. The user reports the prior interaction
polish looks good overall, but holding the slider at either endpoint and moving
slightly repeatedly triggers the Taptic Engine. No new JSON report accompanies
this bug. Prior package identities and the initial haptic compiler failure remain
in [the live-list trial](SWIFTUI_LIVE_LIST_POLISH.md).

## Boundary and correction

The original cycle control used SwiftUI Slider with step 1 and directly assigned
its rounded value to AppStorage on every binding update. It had no Streamside
selection-feedback calls; title-hold feedback is separate. Native slider feedback
therefore was not bounded by an owned selected-value transition. Static inspection
identifies that uncontrolled control boundary, not a measured SDK-internal trace.
Apple's [slider documentation](https://developer.apple.com/documentation/swiftui/slider)
describes its continuous binding changes and discrete step behavior.

The replacement [CycleSlider](../../native/swift/CycleSlider.swift) owns a small
seven-stop native SwiftUI track/thumb. It does not embed a stepped system slider,
so that control's automatic endpoint feedback is removed. Touch coordinates clamp
to the range, and [CycleDetentSelection](../../native/swift/NativeModels.swift)
accepts only a changed selected index. A 0.12-stop margin beyond a midpoint prevents
small movements around the threshold from toggling back and forth. Repeated values,
endpoint overdrag and non-finite coordinates cannot accept a new selection.

There is exactly one explicit UISelectionFeedbackGenerator.selectionChanged call
per accepted and committed selection. No feedback is sent for grabbing a thumb,
stationary holds, release, duplicate callbacks or an attempted VoiceOver adjustment
past an endpoint. Only the first touch prepares feedback; prepare does not request
a pulse. Fast movement can skip unselected intermediate stops rather than queueing
a burst of ticks. Apple's [selection feedback guidance](https://developer.apple.com/documentation/uikit/uiselectionfeedbackgenerator)
is the public API boundary; actual motor output is device/system dependent.

All seven values, the saved preference, labels, left/right direction support and
VoiceOver adjustable actions remain. Reduce Motion still disables and greys the
control; disabled gestures do not capture scrolling. Title-preview haptic ramp/tap,
live rings, account/session/GraphQL logic, and runtime guard coverage are unchanged.
No private UIKit API or global haptic setting is modified.

## Initial validation

Local native tests pass 47/47. Pure Swift model tests replay 1000 small endpoint
moves on each side with zero accepted changes, verify no increment/decrement beyond
the endpoints, traverse the seven choices, clamp large overdrags, reject non-finite
values and verify the midpoint hysteresis. Apple model tests run these same
production selection functions in both builds. These are acceptance/feedback-gating
checks, not physical Taptic measurements or actual drag-gesture execution. Apple
compilation and replacement packaging are pending at the initial implementation
checkpoint. Physical endpoint holding/jittering still requires the device test.
