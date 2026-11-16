# Interactive source-anchored preview

2026-11-16. Branch `feat/native-frontend`, starting revision
`43368080d1f7863df717c2cdfa7b961f8a79669f`.

The [system context-preview trial](SWIFTUI_SYSTEM_CONTEXT_PREVIEW.md#third-apple-build-native-preview-scrolling-limitation)
proved moving decoded video, clipping, both Watch paths and cancellation in the
iOS 26.5 simulator. Its long-details test failed after repeated drags left the
full title and tags unreachable. That failed prototype and its exact build,
logs and screenshot hashes remain preserved. This implementation uses the
previously scoped owned alternative to make the details interactive. It does not
claim that UIKit's context-preview scrolling limitation was corrected.

## Presentation and ownership

`AnchoredPreviewController.swift` installs a child on the existing native root.
It never calls modal presentation APIs, replaces the root, or creates another
window. A snapshot of the selected thumbnail lifts and expands into the live
16:9 video region. The actual video/card expands with the same source geometry,
continuous corners and shadow; the snapshot fades away during entry. A small,
separate SwiftUI action menu uses Liquid Glass on iOS 26 and material on older
supported systems. Only the information/menu surfaces use material, not video.

The details remain a real SwiftUI ScrollView in the view hierarchy. Safe-area
placement reserves room for the separate menu, keeps video at 16:9, and adjusts
the scroll viewport to the remaining height. Short details keep their natural
height. Long titles and all tags remain part of the scroll content. Preview
layout rejects an impossible viewport rather than clipping essential controls.

Outside tap returns the card and thumbnail artwork to the source. An interrupted
entry continues from its current presentation geometry. Source visibility is
restored on removal. There is no X button. Long-press recognition consumes its
release; the user can then inspect or scroll. Normal thumbnail taps and scrolling
remain separate gestures. VoiceOver has a Preview stream action, Watch activation,
escape dismissal and focus restoration. Reduce Motion uses fading, Reduce
Transparency uses opaque information/menu backgrounds, and iOS 16.4 remains the
component floor.

`ContextPreviewSession` retains the same bounded media transaction. It now accepts
a presentation-completion registration instead of a system-menu animator. Account
loss, backgrounding, source removal and failed admission still stop/release once.
Cancellation overrides pending Watch. The presenter removes its child before the
guarded root receives the same TheatrePlayback object. The existing theatre
cross-dissolves and unmutes after presentation. Watch therefore retains the prior
ordered dismissal/transition; its visual timing still requires device review.
The owned preview makes no additional playback request. Native authorization,
IVS/audio services, donor ABI, account restoration and RN/Hermes instrumentation
are unchanged.

## Validation

The existing 74 Linux-compatible native frontend tests passed during implementation.
These cover the current native diagnostic/ABI/emulation and component-admission
boundaries, not execution of the new Apple UI. Apple compilation and simulator
results for this candidate are pending.

The Apple gates retain both existing glass/plain control tests, rendered motion
and opacity checks, actual decoded-video pixel/clipping checks, single-player
Watch and video-tap handoffs, outside dismissal, background/account cancellation,
normal taps and scrolling. The long-details test still requires the final detail
to become hittable, and now explicitly checks the final tag. It has not been
removed or weakened. The fixture samples actual intermediate presentation layers
on both entry and return. Geometry tests check scrolled source coordinates,
video alignment, safe-area/menu placement, rejected impossible sizes, child
containment and interruption cleanup without a presented modal.

The component receipt identifies `source_anchored_preview`, replacing the
superseded system-presentation assertion. All remaining mandatory receipts and
component hash/admission checks remain. Failure logs and bounded owned-fixture
screenshots continue to be exported. No donor IPA or signing material enters CI.
The exact Twitch 32.0 donor identity remains the one recorded by the system trial;
no donor-dependent assembly was performed for this source change.

Submit one build through the existing quota-aware Apple path. Monitoring remains
on hold, so this record does not claim a successful Apple run, a new IPA, physical
IVS compatibility or zero device runtime counts for the replacement. Once Apple
validation passes, perform local donor packaging and review source lift/return,
long-details scrolling, preview silence, handoff and lifecycle behavior on device,
including Reduce Motion/Transparency and the RN/Hermes report.


## Successful Apple build and local package

Source `e883ecfb7e7b3113f36fea4b8fd9ded2d67c8d4c` passed the
[Codemagic build](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afb259c01609fea8f690184).
The [validation record](SWIFTUI_ANCHORED_PREVIEW_VALIDATION.json) preserves exact
source, donor, toolchain, component archive, framework and IPA identities.
This result supersedes the pending-at-submission status above; the failed system
prototype remains recorded separately.

Xcode 26.6 (17F113), Swift 6.3.3 and iPhoneOS SDK 26.5 compiled the arm64 iOS 16.4
component. All five Apple validation stages passed. Four mandatory UI tests
passed with zero failures: glass controls (275.952 seconds), plain controls
(163.227), preview layout/actions (92.295), and thumbnail hold/tap (44.945).
The source animation, outside return, long-details scrolling to the final tag,
actual decoded-video clipping and both single-player handoff paths passed.
These fixtures use AVPlayerLayer with owned H.264 video through the production
passive surface/card/controller. They do not execute Twitch's IVS donor service.
The existing account/root, launch selector, playback lifecycle and networking
gates also passed. Ubuntu verified the downloaded source/hash receipts and all
53 post-download tests before assembly.

The exact local Twitch 32.0 donor SHA-256 was checked again, and native-only
packaging passed all 54 ABI and 25 probe entries, retained-image verification
and unchanged original HBC validation. No independent baseline IPA was created.
The resulting IPA is 196,885,011 bytes; SHA-256:
`415fdf9b6b52267b8c25ce11d28c5aaa57c6d3d279b928f55b23412d13d9b2d3`.
It remains local under the artifact directory and requires Feather signing with
the existing app/keychain identity.

Reproduce from the source revision by fetching its admitted components through
`make native-ci-fetch`, then assembling locally:

```sh
python3 tools/native_frontend/build.py --frontend swiftui --mode native \
  --components ../artifacts/ci/e883ecfb7e7b3113f36fea4b8fd9ded2d67c8d4c/download/components \
  --donor ../donors/tv.twitch-32.0.ipa \
  --output ../artifacts/native-frontend/quick-look-anchored-e883ecf
```

For device review, install with Feather using the same app identity. Hold a live
thumbnail, release and inspect: preview must remain muted, video must keep its
16:9 rounded clipping, and long details/tags must scroll. Tap outside and check
return toward the source. Repeat using Watch stream and a video tap, checking
continuous playback and audio only after theatre opens. Background/reopen,
repeat with Reduce Motion/Transparency, then export Native diagnostics. Physical
IVS behavior, visual feel and zero RN/Hermes counts remain unverified for this
candidate until those results are reviewed.


## Device review and hold/audio refinements

The [device review](SWIFTUI_ANCHORED_PREVIEW_DEVICE_REVIEW.json) matches source
`e883ecfb7e7b3113f36fea4b8fd9ded2d67c8d4c` and its donor/proof. The floating
preview looks better on device. Its return motion was reported as linear with
an abrupt stop; the requested refinement includes a preliminary thumbnail lift.
The report has zero failures, native root ownership, two backgrounds, five
foregrounds and six balanced playback starts/releases/stops. All 25 probe counts
are zero. Baseline calibration is false, so this report alone does not establish
verified runtime absence. The raw report is retained privately with its recorded
SHA-256; the committed summary contains bounded diagnostics only.

The return to source now uses a 0.52-second critically damped UIKit spring.
Apple documents damping ratio 1 as smoothly decelerating without oscillation:
[UIViewPropertyAnimator spring timing](https://developer.apple.com/documentation/uikit/uiviewpropertyanimator/init(duration:dampingratio:animations:)).
Watch and Reduce Motion remain fades. Initial hold feedback enlarges the actual
thumbnail by at most 4.5 percent, starting after 60 milliseconds. The existing
long-press recognizer still admits the preview after 450 milliseconds. Its
possible phase observes touch-down without recognizing a competing gesture.
Early release, movement/scroll failure, source removal and inactivity reset the
feedback. Recognition captures the actual presentation rectangle, resets the
layout view, and starts the floating snapshot from that rectangle to avoid a
snap between stages. The existing single player/media transaction is unchanged.

Muted previews previously configured the same exclusive audio session as theatre;
muting the player did not prevent that session from interrupting other apps.
The owned facade now has explicit preview intent: it forces mute before IVS
creation/load and uses Playback/MoviePlayback with MixWithOthers, without ducking.
[Apple's mixing option](https://developer.apple.com/documentation/avfaudio/avaudiosession/categoryoptions-swift.struct/mixwithothers)
permits concurrent background audio; removing it and activating the session
interrupts other audio. Only the completed, authorized theatre presentation
promotes the existing facade to exclusive audio and then unmutes it. A pending
media request retains this intent and installs the appropriate session when it
loads. Promotion creates no new IVS player or GraphQL request. Dismissal/failure
restores the prior category only if the facade's installed configuration still
owns the shared session. No donor ABI or hooks changed.

The full Linux-compatible suite passed 76 tests after these changes. Apple gates
now additionally require an observed presentation-layer thumbnail enlargement
before preview/player admission, hold cancellation and Reduce Motion behavior,
mixing configured before the synthetic IVS load, restoration after preview
cancellation, and exclusive theatre promotion without another player/request.
The existing decoded-video, clipping, actions, source-return, lifecycle and player
control tests remain mandatory. Apple compilation/simulator validation for this
refinement is pending. Physical testing must play music or a podcast in another
app, open/dismiss multiple previews and confirm uninterrupted audio, then Watch
and confirm that theatre takes over. Device settling/hold feel and the actual
IVS implementation still need review. No new IPA is claimed before Apple passes.


### Hold refinement: first Apple compile failure

Source `1225f0e156e8f17cbf54a1a83eac19e71cb84f57` failed in
[Codemagic build 6afb722101609fea8f6921ba](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afb722101609fea8f6921ba).
The iPhone Swift compile rejected the default value of `beginPress(reduceMotion:)`:
`UIAccessibility.isReduceMotionEnabled` is main-actor isolated, while a default
argument is evaluated in a nonisolated context under the pinned compiler settings.
The archived failure bundle `Streamside_10_artifacts.zip` is retained locally;
2,689 bytes, SHA-256
`822bda94e633fc4d6e70dcc6ac02c457b6c557c29d6d53785021cda54c0a20ff`.

The correction replaces the default argument with a no-argument overload that
reads Reduce Motion inside the main-actor-owned SourceView method, then calls
the explicit Boolean overload. Gesture timing, motion, preview mixing and theatre
promotion are unchanged. No compiler isolation or warning gate was relaxed.
Simulator and audio tests were not reached in this failed run; they remain
mandatory for the replacement. No new IPA was produced. Host tests do not
validate Apple's actor isolation rules.
