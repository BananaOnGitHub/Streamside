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

## First hosted run and test-query correction

Source `5f9310bd09812fed96e27811d3896a961219b2c7` compiled and linked with the
pinned toolchain. The new panel layout/action test passed in 23.872 seconds and
thumbnail gestures passed in 12.443 seconds. The overall
[Codemagic run](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afab05090e83b09c4fae114)
failed in `testGlassControls`: the existing system-share test queried a cell
named Copy, while its first accessibility snapshot exposed Copy only on the
cell's child text. A later snapshot populated the cell label. The real share
sheet and Copy action were present. No candidate was packaged from the failed
run, and subsequent gates were not claimed as passed.

The test now scopes to ActivityListView and finds the action cell containing the
visible Copy text. It still taps the real system action, requires dismissal and
verifies the exact clipboard URL. Timeouts and required gates are unchanged;
there is no retry or skip. Production player/share code is unchanged. The
[failure record](evidence/quick-look-style/first-build-failure.json) preserves the
failed revision, run, assertion and external log hash.

## Corrected hosted run and packaged candidate

Source `acd5911b89fcf2cc1c76690015cd6332fa797cae` passed
[Codemagic build `6afab43790e83b09c4fae23a`](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afab43790e83b09c4fae23a)
in **1,050.885 seconds** (17m 31s). Xcode 26.6 / 17F113 and iPhoneOS SDK 26.5
matched the pin. The quota selector admitted the run with 441 verified free
minutes. Both owned frontend variants compiled, Swift models and required UIKit
lifecycle/playback/ownership fixtures passed, and all four coordinate tests
passed. The corrected system Copy action was tapped and its URL verified in
both player styles; animation frame/pixel checks, compact panel geometry,
long-details scrolling and thumbnail gestures all passed. Foundation networking,
report comparison, logging and provider-routing gates passed. No required gate
was skipped. Linux and documentation CI also passed for this exact revision.
No GitHub Apple or VM duplicate build was started.

Download admission verified source/input identities, toolchain, archive hash and
mandatory receipts. **53 Ubuntu verification tests passed**: 18 ABI, 15 component
admission, 10 diagnostic core, one launch policy, six probes and three launch
comparisons. The owned component archive SHA-256 is
`8ef26e5e444ac0bdbbb34798ee9be2343c0b02cb80d6e7c584a37d749e60aec5`.
Local packaging revalidated the exact inspected donor SHA-256
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`,
all 12 pinned images and native contracts. Retained donor entries and original
HBC were verified unchanged. Only the native IPA was assembled locally; donor,
final IPA and signing material were not uploaded to either build provider.

Candidate `quick-look-style-acd5911/StreamsideNativeProof-Twitch32-native.ipa`
is **196,865,834 bytes**, SHA-256
`2f0fd4d2ad9563771d3cd6e88dbb7ce5dbdab9c23056cbf5dec04648e2245cc8`.
It resides under the sibling `artifacts/native-frontend/` directory. Its hash was
independently recomputed after packaging. Compiler/packaging receipts and logs
remain beside the candidate; failed-run logs remain under the failed source's
external CI directory. [Structured validation](SWIFTUI_QUICK_LOOK_STYLE_VALIDATION.json)
records identities, receipts, timings and the preserved first-run failure.

Reproduce through `make native-ci`, `make native-ci-status`, then
`make native-ci-fetch` on the committed/pushed source. Assemble with
`python3 tools/native_frontend/build.py --frontend swiftui --components
../artifacts/ci/<source-sha>/download/components --donor
../donors/tv.twitch-32.0.ipa --output ../artifacts/native-frontend/<new-name>`.
The [Apple build guide](../development/APPLE_BUILDS.md) owns provider/quota details.

For device review, sign/install with Feather using the existing app identity.
Hold a live thumbnail and inspect the landscape preview, full details and
separate smaller glass action menu. Scroll long details and check that video and
menu stay fixed; try Watch from video and menu, close, background/foreground,
light/dark appearance, larger text and Reduce Transparency. View profile remains
disabled. Export a native report afterward. The supplied prior-candidate report
does not establish appearance or runtime behavior for this new binary; physical
device validation of the restyle remains pending.
