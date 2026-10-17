# RN input covered by keyboard — build 20 trial

Branch: `fix/rn-composer-diagnostics`, following diagnostic commit `1031667`.
Donor: Twitch 31.6.2 (`262872150334984303`).
The [build-19 diagnostic candidate](RN_COMPOSER_DIAGNOSTICS.md) reproduced the
reported input disappearance after opening/dismissing inline-emote information
and reaching the automatic suggestion threshold. On closer device observation,
the input was still visible through the translucent keyboard at the bottom.

## Verified capture findings

The report identifies `3.1.0-build.19`, Composer / Picker + General, Detailed,
active/saved mask 17 and `rn-composer=1`. One provider-details presentation was
counted. Trace retention reached 128 samples out of 465 accepted, with 337
overwritten, zero rate drops, 156 coalesced and 64 retained samples omitted from
export. The exported 64 samples start after the input is already misplaced.
The sheet transition and first appearance of the suggestion row are absent,
so this capture does not locate the first incorrect assignment or establish
whether an earlier editor/component replacement occurred.

Selected numeric observations from that exported window:

| Monotonic ms | State |
| --- | --- |
| 779040594–779041703 | Owner/editor `o2/i2`, first responder, no marked text, no visible sheet or hidden ancestor. Input window rect `[60,800,186,24]`; keyboard `[0,546,402,328]`; window `[402,874]`. The whole input lies under the keyboard, inside the recorded ancestor clipping rectangle. |
| 779040609–779040942 | Committed RN state stays focused, with no suggestion strip, while the draft length decreases from 3 to 0. The covered position persists after suggestions are gone. |
| 779042482 | Keyboard end-frame changes to `[0,874,402,328]` as dismissal begins; input initially remains at y=800. |
| 779042485 | Same editor briefly moves to y=506, a 294-point upward change. |
| 779042492 onward | First-responder flag clears; input animates back toward the bottom. Later hidden-ancestor samples occur during subsequent navigation, not at the initial covered state. |

Throughout the exported native samples, typing/editor/resolved font sizes are
160 tenths of a point and their color is `efeff1ff`. Existing neighboring plain
text has the same style. This capture does not reproduce the separate
small-black-text problem and does not establish its cause.

The input is covered by the keyboard during the captured failure, rather than
being absent, zero-sized or hidden by a recorded ancestor. Losing the keyboard
lift is a supported explanation of the geometry; the exact stale state inside
Twitch/React Native remains unobserved. The two-character trigger remains a
device observation, not a transition preserved in this report.

## Read-only donor follow-up

Inspection of the already admitted, identical 31.6/31.6.2 Hermes body identifies
Twitch's `KeyboardLiftIOS`, `ReanimatedKeyboardLiftIOS`, owned-keyboard tracking
and settled-keyboard synchronization paths. `keyboardLiftTranslateY` (function
35255) adds the signed keyboard height to progress times bottom inset. The
observed 294-point move is consistent with a 328-point height minus a 34-point
inset; that particular inset value was not separately captured.

The owned-keyboard cache updates on will-frame/hide events; the settled path
also subscribes to did-show/frame/hide. These implementations were inspected,
not changed. No source-level replica or host execution of UIKit can prove which
cache, animation value or enabled prop was wrong on this device. No proprietary
donor bytecode is stored in the repository.

## Candidate correction

The owned RN information-sheet route previously presented while its input
could remain first responder. Build 20 ends that editing session by calling
the admitted editor's normal `resignFirstResponder` before presenting the
sheet. Twitch receives the ordinary native end-editing/keyboard-hide lifecycle.
The input stays unfocused when the sheet closes; tapping it starts a new native
focus/keyboard-show cycle.

This is confined to an admitted provider attachment held in the RN composer.
Metadata/attachment/modal/marked-text checks still run first. A refusal to
resign, or a responder that remains active, cancels presentation and increments
a refusal counter. An already-unfocused input needs no resignation. The helper
does not change the draft, selection, attributes, frames, visibility, keyboard
notifications or Twitch's offset stores, and does not automatically refocus.
Native Twitch attachment menus, transcript sheets and the legacy composer use
their existing routes.

The report adds `RN details keyboard resignations/refused`. Event 11 remains
the attempt before the keyboard transition; new event 15 records the ready,
unfocused editor immediately before presentation. The existing bounded trace
remains enabled in this candidate to capture any recurrence and the separate
styling symptom. Event 15 is a native readiness marker, not completion of the
keyboard-hide animation. Device validation is required; the proposal does not
claim the underlying Twitch offset-state defect has been identified or fixed.

## Device check

Keep the existing General + Composer / Picker / Detailed configuration.
After installing build 20, repeat the input-emote hold. The keyboard should
close as information opens. Close or swipe away the sheet, tap the input and
type until suggestions appear. Verify input/suggestions remain above the
keyboard, selection/draft survive, sending works and repeated holds behave
the same way. A failure report should include the new resignation counters.
Continue capturing the rare styling symptom separately.

## Validation and artifact

- Host suite: 196 tests run, 194 passed, two Apple Foundation/ImageIO checks
  skipped on Linux. The 20 RN native composer cases include a new production
  helper regression: resignation precedes presentation, refusal prevents the
  sheet/haptic, repeated inactive-input holds avoid redundant resignations,
  stale metadata and competing modals do not blur, and text/attachment state
  remains unchanged in the controlled host. These are not UIKit device tests.
- Fresh pinned Hermes validation passed: 32 accepted snapshots and 7,344
  window calculations. The native composer/sheet sources and composer tests
  now participate in gate freshness. The owned JS payload and all five exact
  admission/patch stages are unchanged from verified build 19.
- Diagnostic and ordinary native dylib/framework contracts and defined WebP
  symbols passed. Both diagnostic DEB variants were generated.
- The finished diagnostic IPA passed independent `verify_ipa.py`. Direct
  checks confirmed the original HBC, main executable `__text`, `Assets.car`
  and Twitch version/build are preserved, the embedded framework identifies
  `3.1.0.20`, the new counters/trace are present, and the donor IPA's original
  SHA-256 is unchanged after packaging. Documentation validation passed.
- Build 19's published CI completed successfully. Build 20 device acceptance
  remains pending; successful host/package checks do not establish that the
  keyboard symptom is resolved or identify the rare styling defect.

Artifact:

- Filename: `Twitch_31.6.2_Streamside_3.1.0-build.20_composer-keyboard-trial_unsigned.ipa`.
- Bytes: 194,496,020.
- SHA-256: `85d54f83c43b7c6cc536064992ed0a2f7c62558cb6f6d128b5269e46f9cfa9a3`.
- Report/framework: `3.1.0-build.20` / `3.1.0.20`.
- Flags: `RN_COMPOSER_DIAGNOSTIC=1`, `EMOTE_DIAGNOSTIC=0`,
  `IMAGE_DEMAND_DIAGNOSTIC=0`; no experimental transcript trace.
- Original donor SHA-256:
  `8cf72803d0e0b1aeb7c062af2d0cbac1e20f78e9f3c73fc590ac5ae9d1d29186`.

The candidate requires the usual signing route before installation. This trial
keeps the current diagnostic configuration and makes no live ad-suppression
claim. The small-black-text report still needs a separate device capture.

## Device follow-up

Build 20 was accepted on device: the hold/details sequence works, and automatic
suggestions continue working afterward. This supports the scoped editing-session
correction; it does not identify the underlying Twitch keyboard-state defect.
The intermittent small-black-text symptom was not reproduced again and remains
unresolved. No additional instrumentation was added for that symptom.
