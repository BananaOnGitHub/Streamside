# Quick Look preview styling follow-up

Starts from `b2e1f5d` on `feat/native-frontend`. Device review accepted the preview
concept but requested a Safari-like presentation: a landscape preview above
stream details, with a separate smaller action surface below. The working player
ownership, muted start, authenticated services and shared theatre fade remain
unchanged.

## Prior candidate device evidence

The supplied report identifies source
`b89c3f3b7d1e76013b12e2a1b09a9d3cd47130bb`, the expected exact Twitch 32.0 donor
and matching probe contract `4bbaa1a78713a04ee8ba8fb4ae5a81191cdc670140530d378237fc48aa6f03be`.
All 25 monitored entry counts are zero, armed mask is 15, instrumentation failures
are zero, and guarded Streamside root ownership remains 1. Three playback opens,
requests, player creations, playing/decoded observations, releases and closes
were counted. Playback errors and mute mismatch samples are zero. The report
contains two foregrounds and one background; playback was stopped at export.
Counts do not distinguish individual previews from theatre handoffs. Its
baseline-calibrated flag is false, so this is a native-session observation with
existing calibration records separate, rather than a fresh paired baseline test.
The [sanitized summary](evidence/quick-look-style/device-summary.json) preserves
these findings and the raw attachment hash. The raw report remains private in the
previous candidate's external validation folder.

## Presentation change

The SwiftUI presentation now separates the content card and action menu. Video
occupies exactly the card width at 16:9, with no blank vertical expansion. The
full title, avatar/beacon, category and every admitted tag remain beneath it.
Measured content determines details height; only content exceeding the safe-area
budget scrolls, leaving the video fixed. The action surface sits 14 points below
the card, is capped at 280 points wide, and expands to card width at accessibility
text sizes. It contains Watch stream and the disabled View profile row, native
SF glyphs, a separator and pressed feedback.

The menu uses SwiftUI Liquid Glass on iOS 26, system material on older supported
versions and an opaque surface under Reduce Transparency. The feed backdrop uses
system blur, with a dim opaque fallback under Reduce Transparency. This remains
an owned SwiftUI presentation, not a system context menu: retaining the existing
container keeps the preview and theatre fade synchronized without moving
navigation or playback ownership into another presentation lifecycle.

## Validation

Linux native regression suite: **72 passed**. Documentation and whitespace gates
must pass before publication. Hosted coordinate coverage now includes the actual
production panel with short and long synthetic details: 16:9 video, natural card
height, separated narrower menu, on-screen bounds, full-detail scrolling without
moving video, disabled profile and a working glass-menu Watch action. Mandatory
component admission rejects a missing panel receipt. Existing hold/tap/scroll,
player controls, mute-before-load, shared fade, cancellation and lifecycle tests
remain required.

Hosted compilation, packaging identities and outcomes will be appended after
the exact source run completes. Physical-device review remains necessary for
appearance with live IVS video, backdrop, light/dark mode, larger text and Reduce
Transparency. Repeat preview, Watch, close and background/foreground, then export
a native report to check the unchanged runtime guards.
