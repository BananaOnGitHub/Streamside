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
