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


### Hold/audio refinement: successful replacement and package

Source `e50bcc2d0fa03590f84d7c50233b4a96d43411a0` passed
[Codemagic build 6afb784001609fea8f69241c](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afb784001609fea8f69241c).
The [new validation record](SWIFTUI_PREVIEW_MOTION_AUDIO_VALIDATION.json) preserves
this candidate's separate source, donor, component and IPA identities. The first
compile failure and the earlier anchored-preview package retain their original
records and hashes.

Xcode 26.6 (17F113), Swift 6.3.3, iPhoneOS SDK 26.5 and all five Apple stages
passed. All four mandatory coordinate UI tests passed with zero failures:
glass controls (211.626 seconds), plain controls (173.751), preview panel/actions
(78.450), thumbnail hold/tap (48.047). Rendered hold expansion, source targeting,
return motion, full-details scrolling, changing decoded video, clipping, both
single-player handoff paths and cancellation passed. The synthetic native player
fixture passed mixing-before-load, mute enforcement, category restoration after
preview dismissal and exclusive theatre promotion without a new player/request.
Those audio checks use the real AVAudioSession API but a synthetic IVS player;
they cannot prove continued playback from a separate app on a physical device.
Ubuntu component admission and 55 post-download tests also passed.

Local native-only packaging revalidated the Twitch 32.0 donor SHA-256 and all
54 ABI/25 probe entries, retained donor-image checks and unchanged original HBC.
The IPA is 196,888,792 bytes, SHA-256
`64f69e934afc5a6b82f68f5de2de4f7bf8df3291eae6635f3178d8ebae12d113`.
No donor or signing material entered CI, and no separate baseline IPA was made.

Reproduce from that source with its verified component download, then:

```sh
python3 tools/native_frontend/build.py --frontend swiftui --mode native \
  --components ../artifacts/ci/e50bcc2d0fa03590f84d7c50233b4a96d43411a0/download/components \
  --donor ../donors/tv.twitch-32.0.ipa \
  --output ../artifacts/native-frontend/quick-look-motion-audio-e50bcc2
```

Install through Feather using the same application/keychain identity. Play music
or a podcast from another app, then hold a live thumbnail: check the small initial
lift, silent preview and uninterrupted external audio. Tap outside, checking the
smooth return and continued audio. Repeat with Watch stream and a video tap:
only the full theatre should take over audio, retaining the same stream/player.
Also check early release/scroll, Reduce Motion, background/reopen and export Native
diagnostics. Actual IVS/audio behavior and device motion quality remain pending.


## Visible outward hold: clipping correction

2026-11-17. The [next device report](SWIFTUI_PREVIEW_HOLD_DEVICE_REVIEW.json)
matches source `e50bcc2d0fa03590f84d7c50233b4a96d43411a0`, proof and donor.
Preview audio no longer interrupts other media; dismissal looks smoother. Hold
feedback still appears as an inward crop/bounce instead of a gradual outward
pull. The export has zero failures, native root/guard ownership, matching baseline
calibration enabled and all 25 probes zero. Four background transitions and seven
foregrounds are recorded. The original bounded report is retained privately with
its SHA-256. The preceding simulator pass did not establish visible preliminary
motion in the real feed.

Source inspection found two production clipping boundaries: RemoteChannelImage's
`.clipped()` and the thumbnail's rounded clip. Scaling SourceView within these
bounds hides the enlarged edges. The earlier fixture animated a bare representable
and checked its presentation transform; it omitted those clips. That fixture gap
explains why a passing geometric check was insufficient, although no on-device
frame recording was supplied to isolate every part of the reported bounce.

The preliminary animation now uses a passive snapshot added to the existing
window above the clipped feed. The source keeps its layout, transform and hit
gestures; its image is hidden only while the snapshot stands in for it. There
is no new window, root, modal, player or request during this possible phase.
[Apple's snapshot API](https://developer.apple.com/documentation/uikit/uiview/snapshotview(afterscreenupdates:))
supplies the rendered visual stand-in. After 50 milliseconds, a 0.4-second ease-in
progressively enlarges it by up to 14 percent and shifts it toward the estimated
preview video region, with bounded displacement and safe-area clamping. This
replaces the spring press; it does not shrink inward or settle to a preliminary
scale early. Exact card sizing is still deferred until actual preview admission.

At recognition, the actual visible snapshot rectangle is frozen and the same
view object is moved into the existing presenter. The full preview continues
from that position rather than recapturing the clipped source. Early tap removes
feedback before Watch; early release returns it, scroll failure/cancellation or
inactivity removes it immediately. Source disappearance also removes it. Reduce
Motion skips the pull and retains the existing preview fade. The established
0.52-second dismissal spring, authenticated playback, single-player handoff,
audio mixing/promotion, account/root guards and RN instrumentation are unchanged.

The real-video UI fixture now includes both SwiftUI clipping modifiers. Its hold
probe must observe progressive width and position changes AND rendered indigo
fixture pixels beyond the original clipped right edge before player admission.
Captures are bounded to three transient owned-fixture images; no device/feed
artwork is captured by production diagnostics. A layer target alone cannot pass.
UIKit transaction checks cover clipped-source coordinates, reuse of the same
lifted object, early release, inactive cleanup and Reduce Motion. Existing
video clipping, outside return, long-details scrolling, handoff, lifecycle and
player-control gates remain mandatory.

All 76 Linux-compatible frontend tests passed after this correction, along with
documentation/link and whitespace checks. Apple compilation and the strengthened
simulator fixture are pending submission. No new IPA or device visual acceptance
is claimed. Physical review should hold without releasing: the thumbnail should
pull outward toward the preview until it opens, then stay open on release. Also
check short tap/scroll, early cancellation, Reduce Motion and the already-confirmed
external-audio behavior.


### Outward hold: successful Apple validation and package

Source `5ea0a8836d6b0fc1cb79f8d6ae867ffe7777be99` passed
[Codemagic build 6afbfea401609fea8f694bb5](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afbfea401609fea8f694bb5).
The [outward-hold validation record](SWIFTUI_PREVIEW_OUTWARD_HOLD_VALIDATION.json)
retains this candidate's exact source, toolchain, donor and artifact identities.
The previous device findings and package hashes remain unchanged.

All five Apple stages and all four UI tests passed with zero failures: glass
controls (186.509 seconds), plain controls (158.192), preview panel/actions
(79.277), and thumbnail hold/tap (45.138). The strengthened clipped-source test
observed progressive outward growth/translation and rendered artwork beyond the
original thumbnail edge before player creation. Same-object transfer, cancellation,
Reduce Motion, actual decoded-video clipping, full-details scrolling and both
single-player Watch paths passed. Audio mixing/promotion and all existing
root/launch/playback/networking gates also passed. Ubuntu verified the component
archive/source receipts and all 55 post-download tests. These owned-fixture
results establish simulator behavior, not the physical feel or Twitch IVS behavior.

The local donor hash was checked again. Native-only assembly validated 54 ABI
and 25 probe entries, all retained donor images and unchanged original HBC.
The IPA is 196,890,116 bytes, SHA-256
`da234fe9ec5f3ee009ec0790e45ba5182d8c22f431173fde48cc780e9d8f3cd3`.
No independent baseline IPA, donor upload or signing-material transfer occurred.

Reproduce from this source after verified component retrieval:

```sh
python3 tools/native_frontend/build.py --frontend swiftui --mode native \
  --components ../artifacts/ci/5ea0a8836d6b0fc1cb79f8d6ae867ffe7777be99/download/components \
  --donor ../donors/tv.twitch-32.0.ipa \
  --output ../artifacts/native-frontend/quick-look-outward-hold-5ea0a88
```

Install with Feather using the existing application identity. Hold a live
thumbnail without moving: it should gradually pull outward before resolving into
the live preview, then remain open after release. Check short tap, early release,
scroll cancellation, outside return, Watch/video-tap handoff, Reduce Motion and
background/reopen. Keep music or a podcast playing to check that the established
preview audio behavior remains intact. Export Native diagnostics after testing.
Physical-device acceptance for this package is pending.
