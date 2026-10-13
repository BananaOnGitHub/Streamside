# 3.1.0 build 4 — native emoticon proportions

Branch: `dev/3.1.0`; source baseline `01c4d17`. Target: Twitch 31.5
(`262752111271985979`). The RN composer displays classic Twitch emoticons such
as `:)` and `:(` with squeezed proportions. Device acceptance was pending when
this trial was prepared; the follow-up below records the result.

## Image and layout evidence

The inspected native input framework is unchanged from
[the cursor investigation](RN_COMPOSER_CURSOR.md#donor-evidence).
Its attachment-bounds callback at `0x4274` returns the same font-derived value
for width and height (`0x4344`/`0x4348`). Its image decoder at `0x44d8` retains
the input image size when creating the renderer (`0x4544`/`0x4568`). The square
attachment rectangle, rather than a square source bitmap, causes the distortion.

The official CDN's sampled dark 3× images for
[smile, ID 1](https://static-cdn.jtvnw.net/emoticons/v2/1/static/dark/3.0) and
[frown, ID 2](https://static-cdn.jtvnw.net/emoticons/v2/2/static/dark/3.0) are both
72×54 PNGs: aspect 4:3. Sample hashes are respectively
`ca022c35b33b43303db2cd202a96692cdc53633f41185359e916dac3dd856431`
and `5988d86b4e1aa7ad2658904af2e463e930c2aa4cc89378cb037a84da8cef3f90`.
Those samples establish this mismatch; the implementation reads the loaded
image's dimensions instead of hardcoding an emoticon ratio or downloading assets
for layout. CI uses deterministic dimension fixtures, not external CDN access.

The donor's cold-image completion sets the attachment image at `0xbe1c` and
invalidates only display at `0xbfbc`. A changed aspect additionally needs glyph
layout invalidation to update the reserved width.

## Scoped correction

[TASRNComposerUI.c](../../src/TASRNComposerUI.c) reuses the existing exact
attachment class, verified Swift URL field span, and String bridge. It separately
marks positive numeric Twitch CDN IDs below `9000000000`, Streamside's earliest
synthetic reservation. Provider IDs and transcript-width aliases are excluded,
including unknown synthetic identities. Other hosts, malformed IDs, foreign
attachments, and unavailable identity bridges retain the original behavior.

For an admitted native numeric emote with a loaded `UIImage`, attachment width
becomes the original height multiplied by the image's width/height ratio. Native
height, baseline, and paragraph styling remain intact. Square images stay square;
missing images, nonfinite/nonpositive dimensions, and ratios above 20 keep the
original bounds. Known providers retain their existing catalog-aspect path.

The exact attachment class receives an ABI-checked `setImage:` hook, including
when the method is inherited. The original setter always runs. Only native
numeric images whose aspect changed trigger a scan of the existing bounded weak
owner registry. Visible live matches receive single-character layout
invalidation; removed, rebuilt, hidden, detached, and oversized inputs do not.
Every live occurrence is refreshed if an attachment is shared. Equal-aspect image
updates and provider animation frames do not trigger native layout refreshes.

Native numeric attachments enroll their input in the existing eight-owner weak
registry, without adding native decoders or display links. No draft, cursor,
selection, send payload, image transport, Hermes graft, or native menu behavior
is replaced. Diagnostics report only hook availability and aggregate bounds/layout
correction counts. The build-3 cursor guard remains included.

## Verification and device acceptance

[RN composer tests](../../tests/test_rn_composer_ui.py) cover the production
geometry and image-setter hooks under address/undefined-behavior sanitizers with
controlled ABI adapters. The 72×54-to-square regression failed before correction.
New cases cover 4:3 and square images, scaled dimensions, missing/invalid images,
native IDs including 9, reserved/unknown/foreign identities, cold-image arrival,
equal-aspect updates, live repeated attachments, removal/replacement, visibility,
bounded scans, disabled/background fallback, and setter ABI refusal/retry.
These fixtures do not execute UIKit's real layout engine.

Build-4 local validation: 171 host tests run, 168 passed and three skipped (Apple
Foundation and the two private donor/Hermes checks). All 16 RN composer cases
passed. Native dylib/framework contracts, both DEB packages, the developer bundle,
and the final unsigned IPA verification passed. Documentation validation checked
71 Markdown files and 670 explicit references with zero errors. No Hermes or RN
library payload changed in this trial.

On-device checks should include `:)`, `:(`, other classic emoticons, cold and
warm loads, mixed native/provider text, repeated images, wrapping, keyboard/font
changes, background/foreground, and editing/sending. Confirm natural proportions,
unchanged baseline/height, prompt width correction on image arrival, normal native
menus, and the retained cursor behavior. Record the donor/build, device/iOS/signing
route, visible results, and sanitized counters.

Public feature documentation is reconciled at feature freeze under
[Documentation maintenance](../development/DOCUMENTATION.md).

## Device follow-up — 2026-10-13

The build-4 correction on the existing Twitch 31.5 development package was
confirmed to fix the reported emoticon proportions. This establishes acceptance
of the observed visual correction. Device model, iOS version, signing route,
sanitized counters, and results for the complete checklist above were not
recorded; this result does not extend support to Twitch 31.6 or a full device
matrix.
