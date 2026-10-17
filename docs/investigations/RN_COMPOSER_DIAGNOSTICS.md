# RN composer diagnostics — 3.1.0 build 19

Branch: `fix/rn-composer-diagnostics`, based on `dev/3.1.0` at `0a3cf96`.
Target: the supplied decrypted Twitch 31.6.2 (`262872150334984303`).
This candidate investigates two reported RN composer problems:

- Holding a provider emote in the input, opening its information sheet and
  dismissing it leaves the input looking normal until typing reaches the
  automatic two-character suggestion threshold. The input then disappears;
  dismissing the keyboard restores it at the bottom.
- Text typed after an emote occasionally becomes smaller and black. The
  precise insertion/selection history is unknown.

These are separate observations. A shared cause, an upstream hotfix regression,
and any relationship to transcript row gaps have not been established.
The existing `fix/rn-chat-gaps` branch remains paused and untouched.

## Capture instructions

1. Install/sign this diagnostic candidate as usual.
2. Open Streamside settings → Diagnostics. Select Custom, enable General and
   Composer / Picker, disable the other categories, and choose Detailed.
3. Fully close Twitch and relaunch it. The report must identify
   `3.1.0-build.19` and `rn-composer=1`, with Composer / Picker and Detailed
   active. A saved configuration is insufficient until relaunch.
4. In RN chat, open and dismiss input-emote information, then type until
   suggestions appear. When the input disappears, dismiss the keyboard and
   copy the diagnostic report promptly.
5. Capture the small-black-text case separately when it appears. Copy its
   report promptly too. Each report exports the newest 64 samples.

No emote or message contents are needed. Useful accompanying observations are
which symptom occurred, Close versus swipe dismissal, whether the keyboard was
open before the sheet, and native versus provider emote/typed versus picker
insertion if known. Failure to reproduce under instrumentation is also useful;
callbacks and sampling can affect scheduling.

## Inspection findings and implementation

The existing [RN hold](RN_COMPOSER_HOLDS.md) queues the shared native details
sheet without rewriting the draft or explicitly changing keyboard focus.
The owned suggestion wrapper adds a 60-point row at the automatic threshold
and retains the original composer in its second sibling slot. A stale keyboard
inset, clipping or displacement after sheet dismissal is plausible, but a
device trace is needed to distinguish these from unmounting or event ordering.

The original 31.6/31.6.2 RN input executable code is identical, as recorded in
the [hotfix comparison](TWITCH_31_6_HOTFIX_COMPARISON.md). Prior read-only
inspection found that Twitch appends attachment-only attributed strings;
ordinary text uses its default text attributes. Several reconciliation paths
restore typing attributes before setting the selected range. The direct
change-delegate restoration is conditional on empty text. Inheriting incomplete
attributes at an attachment boundary is therefore a hypothesis for the font
symptom, not a confirmed cause. Twitch already restores defaults on several
paths; claiming it never does so would be inaccurate.

[TASComposerTrace.c](../../src/TASComposerTrace.c) adds observational capture
around existing native edit, change, selection and value callbacks, and after
layout/window changes. No original callback, return value, selection request,
draft, typing style, frame or visibility is repaired or replaced.
The trace records:

- Launch-local owner/editor labels, attachment-neighbor flags, bounded UTF-16
  lengths and selection offsets; no text, IDs, attachment URLs or object addresses.
- First-responder, marked-text, sheet-visible and ancestor hidden/alpha state.
- Input bounds converted to its window, window size, intersection of clipping
  ancestor bounds, and last keyboard end-frame converted to that window.
- Font sizes and RGBA colors for typing attributes, editor defaults, guarded
  donor resolved defaults, and the character runs on either side of the caret.
  Marked text suppresses neighboring-run inspection. No font names are stored.

An observer samples at 4 Hz for 15 seconds following native activity, committed
RN diagnostics or keyboard/sheet events. Identical layout/poll states coalesce.
The shared sheet's inherited `viewDidDisappear:` is called first through an
exact-encoding guard; the following marker covers Close and completed swipe
dismissal. Its absence can also mean that runtime guard was unavailable.

The source reads `resolvedFont` and `resolvedTextColor` only if the named ivars
are adjacent pointer fields, inside the admitted owner instance, and the values
have the expected UIKit classes. Otherwise resolved defaults are unavailable.
No hard-coded donor object offsets are used.

[ProviderEmoteStrip.js](../../src/rn/ProviderEmoteStrip.js) emits numeric
committed state, wrapper/strip/input layout, and composer cleanup events through
an optional synchronous `onLayout` export on Streamside's existing private
module. This spelling already exists in the admitted donor's string table.
The export accepts six finite bounded numbers, validates event/session values,
and queues native resampling on the main queue with at most one pending task.
Native input layout callbacks are forwarded unchanged. The optional tracing
method is absent when this module was not compiled or collection was disabled
at launch. Image-demand instrumentation is independent.

## Collection, retention and report boundaries

`RN_COMPOSER_DIAGNOSTIC=1` compiles this module; the build defaults to zero.
Composer / Picker + Detailed must also be active at launch. Disabled collection
returns before UIKit reads, observer installation, bridge export, sampling,
formatting or retention. Summary identifies disabled collection; the general
header identifies compile-time availability.

The numeric ring holds 128 samples, independently of category/HLS event rings.
Capture admits at most 120 samples per monotonic second before UIKit state
inspection. Export includes the newest 64 samples, oldest first, in at most
32 KiB, with explicit overwritten, rate-dropped, coalesced, export-omitted and
capacity-truncation information. Clearing diagnostic history clears this ring.
It keeps no file and resets on process restart. Data are formatted only for
export. The owner watch list is weak and limited to eight live RN inputs;
watch refusals appear in the report.

### Numeric legend

`e` is event, `o` native owner label, `i` native editor label, and `j` JS composer
session label. JS/native labels are independent; temporal correlation does not
prove that two different labels identify the same view. `r` is the input's
window rectangle for native samples or local layout/state values for JS events.
`clip` is the effective clipping rectangle from window/ancestor bounds;
axis-aligned converted bounds do not fully describe arbitrary transforms,
masks, overlays, or occlusion by unrelated views. `hidden` is the first hidden
or nearly-transparent ancestor depth plus one (zero means none).

| Event | Meaning |
| --- | --- |
| 1 | Native layout completed |
| 2 / 3 | Before / after should-change delegate (both precede UIKit insertion) |
| 4 / 5 | Before / after committed change delegate and existing synchronization |
| 6 / 7 | Before / after selection delegate and existing synchronization |
| 8 / 9 | Before / after value prop and existing synchronization |
| 10 | Native move-to-window callback completed |
| 11 | Provider input-details presentation attempted |
| 12 | Poll or queued native sample following a JS observation |
| 13 | Keyboard frame/hide notification |
| 14 | Owned details controller disappeared |
| 20 | Committed JS state: `r=[focused,strip-visible,entry-count,draft-length]` |
| 21 / 22 / 23 | Composer wrapper / suggestion strip / native input JS layout |
| 24 | JS composer effect cleanup (not by itself proof of native destruction) |

`f` is hexadecimal: 1=window, 2=first responder, 4=marked text, 8=sheet visible,
16=keyboard frame known, 32=hidden/alpha≤0.01 ancestor, 64=clipping ancestor,
128=ancestor walk reached its 32-view bound, 256=typing font present,
512=typing color present. `adj` bits 1/2 mark an attachment before/after the
caret; 4/8 mark that attachment as Twitch's emote attachment class. No provider
identity is inferred from those class bits.

`font[t,b,r,prev,next]` gives typing/editor/resolved/previous-run/next-run sizes
in tenths of a point; -1 means unavailable. Colors use the same ordering as
packed RGBA hex, resolved against the editor's traits where supported.
Zero can mean unavailable or transparent black; presence flags disambiguate
missing typing keys. Coordinates are rounded points, bounded to ±100,000;
-100001 marks nonfinite input. Length/selection 4097 means over the inspection
bound, including unavailable `NSNotFound` selection. Missing windows produce
zero geometry; flags distinguish this from a real zero-sized view.

## Validation and artifact

- Full host suite: 195 tests run, 193 passed, two Apple Foundation/ImageIO
  integration checks skipped on Linux. The new collector/bridge fixture runs
  production capture and validation code with typed Objective-C host adapters
  under address/undefined-behavior sanitizers. It covers unchanged editor
  state, missing/incorrect typing style, ancestor visibility, neighboring
  attachment flags, marked-text inspection refusal, disabled argument
  evaluation, rate limits, retention/overflow/export, malformed packets and
  history clearing. The normal-build fixture links without an Objective-C
  runtime. The existing report-routing fixture was extended for both compile
  configurations after its first invocation exposed the missing new define.
- The source JS behavior checks cover the threshold transition, numeric-only
  committed/layout packets, unchanged native layout callback forwarding,
  original composer placement and preserved explicit input font/color props.
- Full five-stage structural verification passed against the exact 31.6.2
  IPA: deterministic generation of 139 owned strip functions, original Metro
  bindings, all 48,996 predecessor functions, original constants/handlers/debug
  data and independent Hermes-98 disassembly. Admission hashes/lengths were
  not weakened.
- The pinned Hermes gate passed with the actual donor, 32 accepted snapshots
  and 7,344 window calculations, including the existing donor settings and
  list-window checks. New trace sources/tests participate in its freshness
  fingerprint. Diagnostic builds require that current gate.
- Diagnostic and ordinary dylib/framework artifacts passed native Mach-O and
  defined WebP-symbol verification. The diagnostic framework contains the
  trace entrypoints and module export; both DEB variants were built.
- The finished IPA passed independent `verify_ipa.py`. Direct archive checks
  confirmed unchanged original HBC, main executable `__text`, `Assets.car` and
  Twitch version/build, framework build `3.1.0.19`, compiled trace content, and
  the original donor hash after packaging. Documentation validation passed.

Final artifact:

- Filename: `Twitch_31.6.2_Streamside_3.1.0-build.19_composer-diagnostic_unsigned.ipa`.
- Bytes: 194,495,925.
- SHA-256: `edc4e33d898fc37292e23fa94fb53d1e55b9c1ca3f3da9a22830a6760ab39f20`.
- Flags: `RN_COMPOSER_DIAGNOSTIC=1`, `EMOTE_DIAGNOSTIC=0`,
  `IMAGE_DEMAND_DIAGNOSTIC=0`; no experimental transcript trace.
- Report: `3.1.0-build.19`; framework: `3.1.0.19`.
- Supplied donor: 197,132,394 bytes, SHA-256
  `8cf72803d0e0b1aeb7c062af2d0cbac1e20f78e9f3c73fc590ac5ae9d1d29186`.

The IPA requires the usual signing route. Both symptoms still require device
capture; this candidate does not claim either is fixed. Host fixtures do not
reproduce UIKit keyboard/Fabric behavior, and packaging does not establish live
playback or ad suppression on a device.
