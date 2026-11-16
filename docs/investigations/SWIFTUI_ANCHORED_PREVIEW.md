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
