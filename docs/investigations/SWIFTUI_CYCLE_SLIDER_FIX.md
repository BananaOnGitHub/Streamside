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
past an endpoint. Touch start and accepted transitions prepare feedback; prepare does not request
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


## Successful build and packages

Compiled/packaged source: `866bd92d7322d71cc7413d82a7a1e49298e1666f`.
[Artifact receipts](SWIFTUI_CYCLE_SLIDER_FIX_ARTIFACTS.json) record proof, exact
source/donor/toolchain identities, independently verified IPA hashes and framework/
modified-image/manifest hashes. Outputs remain outside the source checkout.

[Apple Actions 43324820685](https://github.com/BananaOnGitHub/Streamside/actions/runs/43324820685)
succeeded with pinned Xcode 26.6 / 17F113, Swift 6.3.3 and iPhoneOS SDK 26.5.
Both frameworks compiled/linked and passed signature verification. Both Apple
model programs passed the new endpoint/midpoint acceptance tests, and existing
real UIKit ownership, clock, title-measurement and haptic-pattern fixtures passed.
ABI 12, component admission 9, core 8, Foundation 1 and synthetic comparison 5
checks passed. Local native checks passed 47/47.

[Linux Actions 43324820563](https://github.com/BananaOnGitHub/Streamside/actions/runs/43324820563)
succeeded: 224 tests, 220 passed and four skipped (Apple Foundation/ImageIO and
missing legacy donor/Hermes runner). Documentation checks pass. Neither this
workflow nor the simulator measures actual Taptic output or replays finger input
through the new SwiftUI gesture. Physical endpoint validation remains pending.

Local assembly re-admitted the exact Twitch 32.0 donor, 40 native ABI entries and
unchanged 25 probes, verified retained donor contents and unchanged HBC, and checked
output ZIP/images. No donor, IPA or signing credential went to public CI. Both
IPAs require Feather signing with the established application/keychain identity.
Public release documentation and earlier trial outcomes remain unchanged.

Reproduction (source/proof-compatible checkout, empty external output):

```sh
gh run download 43324820685 --name swiftui-components-866bd92d7322d71cc7413d82a7a1e49298e1666f --dir ../artifacts/ci/866bd92d7322d71cc7413d82a7a1e49298e1666f
python3 tools/native_frontend/components.py verify --output ../artifacts/ci/866bd92d7322d71cc7413d82a7a1e49298e1666f
python3 tools/native_frontend/build.py --donor ../donors/tv.twitch-32.0.ipa --frontend swiftui --components ../artifacts/ci/866bd92d7322d71cc7413d82a7a1e49298e1666f --mode both --output ../artifacts/native-frontend/swiftui/cycle-slider-rebuild
```

Rebuild the pinned source workflow after component expiration. Replacement
assemblies receive their own identities; earlier hashes are not overwritten.

## Device regression check

1. Sign/install the matching baseline with Feather, open Twitch and export reports.
   Replace it with the native IPA using the same identity. The new source proof
   needs its own baseline positive control.
2. Open Settings. Drag to 0.5s, hold and move slightly for several seconds, then
   repeat at Off. An actual arrival at a changed selection should tick once;
   holding/jittering/releasing there should not tick again. Touching an endpoint
   already selected should have no selection feedback at all.
3. Move between adjacent stops and jitter around a midpoint. Expect one tick per
   accepted new stop with no threshold chatter. Verify all labels/choices still
   select correctly and survive reopening. VoiceOver attempts beyond the ends
   should not request another selection tick. Reduce Motion must keep the control
   greyed/disabled and preserve the saved choice.
4. Check title-preview haptics still work separately, then refresh and background/
   return and export. Require calibrated/armed monitoring, root ownership 1, zero
   failures and zero guarded RN/Hermes/worklet entry counts. Preserve reports and
   the observed reproduction if the endpoint motor spam persists.

No new device success is claimed until that endpoint hold-and-jitter check is
performed. The fix removes the automatic stepped-control feedback path and tests
its owned selection gate; it does not assert an SDK-internal haptic trace.
