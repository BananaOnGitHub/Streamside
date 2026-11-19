# Inline marked-content warning polish

Starting branch `feat/native-frontend`, commit `fcfcd73`. The preceding IPA/source
is `6ef88b01dd1025a1e2c41c8234d9da1e5550913c`. Its
[device review](SWIFTUI_MARKED_CONTENT_INLINE_DEVICE_REVIEW_1.json) matches the
source/proof/donor and confirms functioning inline warnings with three requested
changes. Raw diagnostics and the screenshot are retained privately alongside that
IPA; only scoped observations and hashes are committed. The export reports zero
failures, eight successful playback cycles, no mute mismatches and 25 probe counts
at zero. Calibration is false and no paired baseline is attached; this does not
independently prove runtime absence. Earlier failures and the successful Apple
[validation record](SWIFTUI_MARKED_CONTENT_INLINE_VALIDATION.json) retain their
original scope.

## Changes

The consent gate reads the current saved thumbnail preference at Continue. If
Don't show again is selected and marked thumbnails are already enabled, it saves
the warning choice and admits playback immediately, without presenting the
thumbnail question or rewriting the thumbnail setting. With thumbnails off it
still asks before playback. The first warning is never bypassed by the thumbnail
setting, and Close still discards the checkbox. Both preview and theatre use the
same gate and existing authenticated playback facade.

The warning fits a centered, compact message/action group inside the video area.
Subheadline text, a larger eye icon and regular-size actions replace caption/mini
controls. ViewThatFits uses a scrollable-message/fixed-actions fallback for long
labels and accessibility sizes. Existing Liquid Glass, Reduce Transparency and
older-iOS button fallbacks remain. No custom animation or media ownership change
is introduced.

Preview playback status moves out of the scrolling channel details into a fixed
footer with horizontal/bottom insets. Panel measurement reserves a normal status
row even while consent hides it, so admitting playback does not resize the card.
Long titles and tags still scroll, while Buffering and its spinner retain their
own space above the rounded card boundary. The actual video remains 16:9.

## Validation scope

The Apple model test covers an already-enabled preference, reading its current
value at Continue, preservation on Close and no redundant thumbnail write. Its
success marker is mandatory. The existing consent coordinate test retains all
prior cases and adds enabled-thumbnail admission in both destinations, zero
media starts before consent, exactly one afterward, centered/compact geometry
and larger contained actions. The existing real-video preview test also uses the
production status footer: text/spinner containment before/after long-details
scrolling, fixed status position, decoded colors, corner clipping and single
player handoff all remain required. No mandatory gate is removed or retried.

Linux host checks do not compile SwiftUI or validate appearance. Apple compilation
and simulator execution of these changes are pending at implementation time.
Physical-device review of the new layout, actual preference combinations and
buffering behavior is still required. No donor/signing material goes to CI; local
packaging follows a successful source-matched component build.

Local validation before the implementation commit: all 94 native host/donor and
orchestration checks passed in 11.346 seconds. The final log SHA-256 is
`7839afe20348fd0e63eb337878faeae6968dff24e5d70b5f85c3fcf267471872`.
Documentation validation checked 124 Markdown files and 1217 references with zero
errors; staged whitespace validation also passed. These results do not execute
the new Swift model or coordinate assertions, which remain Apple-only.

## First polish build: constrained canvas correction

Source `cc38c6c42ea333c0a67ba612b183f13dff690057` compiled and passed the new
existing-thumbnail preference model regression. The coordinate test then found
the first preview's warning had negotiated a 161.3 × 136 point box within the
360-point card, with zero height left for its message scroll area. The
[failed-build record](SWIFTUI_MARKED_CONTENT_INLINE_POLISH_BUILD_FAILURE_1.json)
retains the exact run, screenshot/archive/log hashes and scope. The later enabled
thumbnail and buffering-footer coordinate checks were not reached.

The correction makes video geometry independent of the warning's ideal content
size. The warning reads the actual canvas proposal with GeometryReader and gives
both ViewThatFits candidates that fixed inset width and available height. The
theatre uses a 16:9 background canvas with the warning overlaid, matching the
preview's externally fixed video dimensions; the coordinate fixture uses the
same canvas construction. The test retains all aspect/containment/hittability
requirements and also requires the full expected video width, so a smaller box
with the correct ratio cannot pass. Larger centered controls and the long-label
scroll fallback remain. All 94 host checks passed; corrected Apple layout and
physical-device appearance remain pending.

## Second polish build: physical card boundary for containment

Source `9d5e1ebb95daf76bc5e79e80bd8d3174aad495b5` passed all seven inline consent
cases, including enabled-thumbnail admission, centered larger controls and the
full-width canvas. Both glass/plain animation and rendered-pixel tests passed.
The [second failure record](SWIFTUI_MARKED_CONTENT_INLINE_POLISH_BUILD_FAILURE_2.json)
preserves a subsequent status-containment failure in the first short preview.

The test compared the footer against SwiftUI's tight accessibility content bounds
(345 points tall), while the actual rounded UIKit card was 358.1 points tall.
The former excludes bottom padding and ended at the footer text. The screenshot
shows the text and spinner inside the actual card. Archived hierarchy values are
rounded; this finding does not assert a precise floating-point edge difference.

The corrected test identifies the actual QuickLookController view that owns
corner clipping and checks its full video-plus-details dimensions before using
its bounds. Its identifier leaves the view a container rather than a VoiceOver
leaf. Text/spinner containment remains required before and after long-details
scrolling, with an additional minimum 10-point bottom clearance. Menu separation
and compact sizing use the same physical boundary. The SwiftUI content container
continues to own scroll queries. Actual changing decoded video, corner clipping
and single-player Watch checks remain mandatory. No visual, playback, preference
or navigation behavior changes in this correction. All 94 host checks passed;
corrected Apple execution and physical-device validation remain pending.

## Successful polish build: 91630d0

[Codemagic build 6afe46efd133a39c4a12f044](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afe46efd133a39c4a12f044)
passed all six CI stages for source
`91630d004b260f0e27775af29616da6a1da552f9`. Its
[validation record](SWIFTUI_MARKED_CONTENT_INLINE_POLISH_VALIDATION.json) contains
source/proof/toolchain identities, receipts, archive/IPA hashes and reproduction
inputs. All five coordinate tests passed, including all seven consent cases,
full-width compact warning geometry, enabled-thumbnail admission in both views,
and status text/spinner containment with bottom clearance before/after scrolling.
Glass/plain fade pixels and all three decoded-video handoffs also passed.

The downloaded components passed 66 host checks. Local native-only IPA assembly
verified the exact Twitch 32.0 donor, all retained entries and unchanged HBC.
No separate baseline IPA, remote donor transfer or signing-material upload was
needed. The earlier failed records retain their original scope. These results establish
Apple/synthetic and package validation; the revised warning appearance, real
preference combinations and loading status still require device review.
