# Marked-stream consent inside the video area

Starting state: `527af99` on `feat/native-frontend`. The preceding component/IPA
source is `f6d279ca48790d3960c40dced53360242fd591c0`. The
[device review](SWIFTUI_MARKED_CONTENT_DEVICE_REVIEW_1.json) preserves the supplied
report identity and scoped observations: functional confirmation, ten successful
playback cycles, zero playback failures and all 25 probe counts zero. The report
advertises calibration but no fresh paired baseline accompanies it. The prior
[warning implementation and failures](SWIFTUI_MARKED_CONTENT.md) remain historical
evidence; this successor changes its presentation and media-admission ownership.

## Implementation

The preview and portrait theatre open their existing hierarchy immediately. The
warning, loading/failure states and thumbnail question replace only the 16:9
video slot. Channel identity/details and the separate preview action menu remain
visible. Close dismisses the preview or theatre itself, including from the
thumbnail question. Continue and the independent saved preferences retain their
previous behavior; first-warning Close still discards the checkbox.

The warning's scrollable label area and fixed action area keep actions within
the video frame. Buttons use Apple's iOS 26
[glass](https://developer.apple.com/documentation/swiftui/primitivebuttonstyle/glass)
and [glassProminent](https://developer.apple.com/documentation/swiftui/primitivebuttonstyle/glassprominent)
styles, respecting the existing Liquid Glass preference and Reduce Transparency.
Earlier supported iOS versions and opaque presentation use bordered controls.
No custom motion is added to these controls. The full-window consent controller
and pre-presentation root interception have been removed.

[TheatrePlayback](../../native/swift/TheatrePlayback.swift) is extracted from the
theatre view as the existing shared media facade. It now holds pending consent.
Constructing that facade creates no IVS player, playback request or audio setup;
`start` waits for consent and any thumbnail choice. The native CCL request still
uses the exact previously inspected authenticated Twitch-native query. No new
donor ABI or hooks are added; the exact 32.0 donor and 67 admitted ABI boundaries
remain pinned. Account access restrictions still apply independently.

The same facade and gate survive Watch into theatre. Navigation ownership is
rebound so Close affects the current destination. Before media starts, native
`enterTheatre` changes playback intent only; it performs no audio activation or
IVS initialization. After real preview playback starts, the existing native
promotion retains its established behavior. Cancellation clears consent before
stopping media, so a late label response cannot start playback or close a newer
owner. Theatre background/account loss and preview transaction cancellation
close pending consent and cancel the native label request.

The preview's UIKit video tap button now yields hit testing and accessibility to
consent controls until admission. After admission it resumes its normal Watch
behavior. Outside dismissal, swipe dismissal, source animation and the menu keep
their existing ownership. A pending Watch can navigate to theatre with the warning
still in the video slot; it does not acknowledge the warning or start media.

## Validation

[Linux host validation](SWIFTUI_MARKED_CONTENT_INLINE_HOST_VALIDATION.json) passed
91 native host/donor tests and 12 provider-routing tests. This does not compile
the SwiftUI changes or execute the new Apple-only fixtures.
The Apple path keeps the existing mandatory gates and adds:

- A host fixture executing the production playback/consent state machines with
  only the media boundary stubbed: one label request, no early media start,
  discard-on-Close, same-facade pending Watch, thumbnail choice before start,
  late cancellation and current-owner Close.
- The real Objective-C playback fixture checks pending promotion creates no
  player, request or audio activation and does not change the audio category.
- The coordinate fixture uses the production warning, playback facade, source
  presenter, transaction and menu. It checks 16:9 containment, actual warning
  button touches in preview, both Close paths, pending Watch and exactly one
  media start after the final choice. Existing glass/plain, animation, decoded
  video, source gestures and lifecycle tests remain mandatory.
- Component verification requires the new inline admission, pending Watch and
  native promotion results; missing evidence rejects the component.

The SwiftUI/Objective-C changes still require a successful Apple build. The
fixtures use synthetic labels and media boundaries. They do not establish the
new presentation's device appearance, real Twitch label retrieval, thumbnails,
external-media preservation or RN/Hermes counters. No replacement IPA/device
success is claimed at implementation time.

## Device checks for the replacement

1. Re-enable Show marked stream warnings. Open a marked stream by tap and by
   long press: the existing destination should open with consent inside its
   video rectangle, and Liquid Glass actions should respond without starting audio.
2. Select Don't show again, then Close: the destination should close and warn
   again on the next opening. Continue without remembering should start playback.
3. Continue while remembering: the thumbnail question should remain in the same
   video rectangle. Either thumbnail choice must finish before media begins.
4. From a pending preview, choose Watch: the same warning should move to the
   theatre without media starting. Continue or Close must affect that theatre.
5. Check outside/swipe dismissal, background/account cancellation, first preview
   with external audio, post-consent Watch, both glass settings and Reduce
   Transparency. Export Native diagnostics after exercising these paths.

## First inline build failure and correction

Source `82bdcb11b1986f8b679c8033de7e42499a1f0737` compiled on Apple CI,
but the coordinate test found the preview checkbox was not hittable. Both
direct-theatre sequences and the four other coordinate tests passed. The
[failed-build record](SWIFTUI_MARKED_CONTENT_INLINE_BUILD_FAILURE_1.json) retains
the build, archive/screenshot hashes, hierarchy findings and validation limits.
Raw evidence is retained outside the active artifact directory.

The Watch overlay was still exposed above the warning in the accessibility
hierarchy. Its point-testing/accessibility overrides were insufficient. The
correction observes the main-actor playback gate and hides the actual UIKit
button, disables interaction and removes accessibility participation until final
admission. The initial gate value is delivered synchronously; subsequent changes
restore Watch without polling. Detachment cancels the observation. The synthetic
warning fixture is also aligned to the card top, matching the production panel.

The mandatory coordinate test retains its hittability and video containment
assertions. It additionally checks actual checkbox selection, absence of the
video Watch target during consent, and restoration of that same target after
preview admission. Preview acceptance before Watch and pending Watch before
acceptance are separate cases, both requiring exactly one media start. Apple
execution of this correction and physical-device validation remain pending.

## Second inline build: consent passes, render checks fail

Source `875f77e8ca65c72f9bdb3845ac547d5a32aef2d3` compiled and passed the
complete inline consent coordinate sequence, including checkbox touches and both
Watch orders. The [second failure record](SWIFTUI_MARKED_CONTENT_INLINE_BUILD_FAILURE_2.json)
preserves that result separately from two existing visual-test failures. Plain
controls sampled only through progress 0.792 on the forced-fade entry. The
long-details preview then failed to observe decoded colors after theatre
transfer; both preceding short-details handoffs passed. Its decoder state is
unknown, so this is not classified as a runner-only issue or a resolved playback
defect. No component/IPA success is claimed.

The combined coordinate command hit its 900-second limit during the final test,
preventing result-bundle finalization and screenshot export. The corrected runner
executes the same five mandatory tests in separate bounded commands and unique
result bundles, stopping on failure to export that test's evidence. It still
requires all five successes and all visual markers before producing a receipt.
There are no automatic test retries or skipped checks.

Motion sampling now waits for an observed intermediate modifier frame and its
endpoint instead of assuming a fixed sleep after a state assignment is a render
barrier. Existing coverage, synchronization, movement and decoded/pixel thresholds
remain unchanged. Terminal negative results fail promptly. Video sampling uses
one coherent bounds query rather than four accessibility requests per pixel.
The donor-free decoder surface exposes current player/item/layer status, time
and window attachment for a failed handoff, without a timer or SwiftUI mutation.
These changes require Apple execution; the long-details handoff remains an open
validation item until changing decoded frames are observed in theatre. Production
playback and navigation code are unchanged by this test-runner correction.
