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
