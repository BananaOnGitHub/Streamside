# Twitch 31.6 compatibility inspection

> Follow-up: [3.1.0 build 5 ports the Hermes chain](#build-5-hermes-port) to the
> same 31.6 donor. The original inspection below describes source `ba7dd0b` and
> its refusal; it is preserved as the pre-port result. Host port validation now
> passes, while 31.6 device acceptance remains pending.

Inspected 2026-10-13 on `dev/3.1.0`, source `ba7dd0b` (Streamside 3.1.0 build 4).
This is donor inspection, not a completed port or device acceptance. Twitch
31.5 remains the admitted RN donor. The separate
[build-4 follow-up](NATIVE_EMOTICON_PROPORTIONS.md#device-follow-up--2026-10-13)
records acceptance of the emoticon correction on 31.5.

## Inputs and identity

The supplied decrypted `tv.twitch-31.6.ipa` was compared with the verified
`Twitch_31.5_Streamside_3.1.0-build.4_unsigned.ipa`. The baseline package preserves
the original 31.5 Hermes body and Twitch native code; its injected Streamside
framework is excluded from donor-removal conclusions.

| Property | 31.5 baseline | 31.6 input |
| --- | --- | --- |
| Twitch build | 262752111271985979 | 262821841498166537 |
| IPA bytes | 192,534,474 | 197,132,043 |
| Bundle/executable | `tv.twitch` / `Twitch` | `tv.twitch` / `Twitch` |
| App minimum iOS | 16.4 | 16.4 |
| Build SDK | `iphoneos26.5` | `iphoneos26.5` |
| `UIDesignRequiresCompatibility` | true | true |
| Original Hermes version | 98 | 98 |
| Original Hermes bytes | 27,786,480 | 28,682,408 |
| Original Hermes functions | 47,311 | 48,985 |

IPA SHA-256 identities:

- 31.5 baseline: `78f36aaf40a1b900483ba5786b3cef3a37d286f9eec3a9da4d63112d954aba64`.
- 31.6 input: `36d85ac4a7f0979ca392415af697a43fe7eb019f7fbfdf84dce18b7a25249cea`.

Original Hermes SHA-256 identities:

- 31.5: `422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b`.
- 31.6: `20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458`.

Both original Hermes SHA-1 footers validate. Inspected main executables and
framework binaries have no nonzero encryption IDs. The identical minimum and
compatibility flag are package metadata observations, not new device or Liquid
Glass acceptance evidence.

## Definite RN incompatibility

The original 31.6 body is 895,928 bytes larger and contains 1,674 additional
functions. [TASRNWidthPatch.h](../../src/TASRNWidthPatch.h) admits the exact
31.5 body; [TASEmotes.c](../../src/TASEmotes.c) checks that body length before
attempting the patch chain. The 31.6 body fails that first length condition.

A temporary Linux C wrapper compiled the production headers unchanged with
Zig 0.14.0. A Python `hashlib.sha1` callback supplied the checksum operation.
The original bodies were then passed to the actual patch functions:

| Production stage | 31.5 result bytes | 31.6 result |
| --- | --- | --- |
| Width | 27,787,687 | Refused; null result, zero result length |
| Local echo | 27,788,032 | Not reached |
| Composer | 27,794,428 | Not reached |
| Popup | 27,797,044 | Not reached |
| Strip/library | 27,827,572 | Not reached |

Every accepted 31.5 output had a valid recomputed footer. Both donors' supplied
input buffers remained unchanged. This verifies the current refusal and gives
the 31.5 positive control; it does not execute a 31.6 graft.

The RN width, own-message, provider composer map, details, suggestions, and
library integrations therefore cannot be considered supported on 31.6. Native
incoming-frame rewriting is separate: when width readiness is false it can
still use the older nonproportional transform. Refusal is not a claim that every
provider emote becomes literal text or that every native hook is disabled.

Changing only the expected size or checksum would not establish compatibility.
Re-resolve donor function headers, Metro modules, exports, registers, branches,
and exception ranges, regenerate the owned payloads, and run the exact-donor and
compiled-runtime checks in [Twitch internals](../development/TWITCH_INTERNALS.md)
before device acceptance.

## Native comparison

Compare `__text` bytes rather than whole signed Mach-O hashes. Full binary
hashes differ even for unchanged executable sections. Of 62 common images
(main executable plus 61 Twitch frameworks), 53 have identical `__text` bytes
and nine differ.

Relevant unchanged executable sections include `twitch_rn_emote_input`, `React`,
`hermesvm`, `FLAnimatedImage`, `AmazonIVSPlayer`, `twitch_rn_animated_image`,
`ReactCodegen`, `ReactNativeDependencies`, `ReactAppDependencyProvider`, and
`react_native_keyboard_controller`.

The nine changed sections are the main executable, `KMPMobileChat`,
`OrderedCollections_1222128174265B56_PackageProduct`, `TwitchCore`,
`TwitchGraphQLAPI`, `TwitchKit`, `TwitchUtilities`, `twitch_rn_debug_props`, and
`twitch_rn_player`. Three frameworks were added:
`Atomics_301F3DE065572157_PackageProduct`,
`DequeModule_307A0402D40AB265_PackageProduct`, and
`InternalCollectionsUtilities`. No baseline Twitch framework was removed.

Read-only Objective-C inspection covered 43 source-referenced donor classes
and 595 directly declared instance/class methods. Their method sets and full
encodings match between the two donors, including RN source/socket, native RN
input, legacy composer/picker, presentation, and image boundaries. This comparison
does not validate inherited UIKit methods or private Swift function semantics.
`TKIdentity`, also requested by the source, was not located in either donor's
class lists; that is an inspection gap, not a newly removed class.

The metadata reader from historical source `040a0d1` was reused for framework
metadata. The main executable additionally required resolving its
`DYLD_CHAINED_PTR_64_OFFSET` rebases in a private analysis copy. Runtime-initialized
Swift offsets remain unresolved; zero-filled/static zero values are not live
offset evidence. No donor file was modified by metadata inspection.

The native RN owner and attachment layouts match. Important owner offsets are
`textView` 8, `emoteMapDict` 16, `currentPlainText` 48, `imageCache` 64,
`selection` 392, and `selectionGeneration` 400. Attachment `url` begins at 24
and `loaded` at 40, preserving the 16-byte String span. The identical native
input code supports carrying forward the
[cursor guard](RN_COMPOSER_CURSOR.md) and
[proportions correction](NATIVE_EMOTICON_PROPORTIONS.md); changed JS scheduling
and real UIKit behavior still require device verification.

Two inspected legacy classes changed layout declarations:

- `EmoteManager` adds a 128-byte `_graphQL` field. Instance size changes from
  320 to 448; `currentUserID` moves from 280 to 408 and `recommendedEmotes` from
  288 to 416. The eight-byte span, alignment, and instance-bound conditions used
  by [TASEmotePresentation.c](../../src/TASEmotePresentation.c) remain satisfied.
  The implementation resolves named ivars rather than hardcoding offset 280.
- `SkylineLiveChat` adds `_graphQL` and its declared size changes from 1010 to
  1138. Relevant Swift field offsets are initialized at runtime, so static
  equality cannot admit the live connection/picker traversal in
  [SSComposer.c](../../src/SSComposer.c).

No additional definite native ABI break was found in these inspected
declarations. Matching signatures do not prove that callback routing, catalog
publication, live ownership, or Swift value-witness behavior is unchanged.

## Packaging and playback boundaries

The ordinary [IPA patcher](../../tools/patch_ipa.py) and
[IPA verifier](../../tools/verify_ipa.py) are used separately from RN admission.
The packaging probe with the existing verified build-4 framework passed ZIP
integrity, load-command insertion, owned framework bytes/metadata, icon assets,
and preservation of `Assets.car`. The unsigned output was an internal inspection
artifact, not a release candidate. Packaging success does not make the RN bundle
compatible or establish launch, signing, Liquid Glass, or playback acceptance.

[Streamside.c](../../src/Streamside.c) hooks Foundation/AVFoundation rather than
a Twitch-version-specific player offset. The inspected `AmazonIVSPlayer` code
is unchanged, while `twitch_rn_player` changed. Neither observation proves that
31.6 still takes the intercepted request path or emits the same token/manifest
operations. Live playback, an actual ad-bearing case, token refresh, recovery,
and background/foreground behavior require device evidence.

## Outcome and next acceptance boundary

Documentation validation checked 72 Markdown files and 684 explicit references
with zero errors. All 29 documentation-validator unit tests passed, with no
skips. The inspection used the existing build-4 framework and production patch
headers; no source, version metadata, workflow, or admission constants changed.

The current RN integration is incompatible with the inspected 31.6 donor.
Retain 31.5 admission and the existing checks while porting the changed Hermes
bundle. Native inspection found plausible carryover boundaries, with legacy
runtime layout and playback questions still open. No 31.6 device test, signer
test, or release acceptance was performed in this inspection.

At the port's acceptance boundary, check actual RN/legacy routing, incoming and
ordinary sent emotes, native/provider composition, holds, cursor continuation,
classic emoticon proportions, cold images, suggestions/library/settings,
account/channel changes, and lifecycle behavior. Record exact donor/artifact
identities and failures under
[Documentation maintenance](../development/DOCUMENTATION.md).

## Build 5 Hermes port

Streamside 3.1.0 build 5 ports all five stages to Twitch 31.6
(`262821841498166537`), prepared from source parent `8eae51b` with the changes
in this port. The input and original Hermes SHA-256 identities remain those
recorded above. Admission now requires the exact 28,682,408-byte Hermes-98
body and its pinned SHA-1 footer `d2428c8fa344f3956c89b991c4bd488b42a12db7`.
This development build targets 31.6 only: the old 31.5 body is refused. Build 4
and released 3.0.0 retain their 31.5 scope.

### Resolved seams and chain

| Stage | Original donor function / bytes | In-memory result bytes |
| --- | --- | --- |
| Width | EmotePart 18563 / 943 | 28,683,611 |
| Local echo | onChatEvent 35388 / 121 | 28,683,956 |
| Composer | ChatComposerBar 22516 / 6488 | 28,690,600 |
| Popup | ChatCardHost factory 3694 / 600 | 28,693,212 |
| Strip/library | ChatComposerBar factory 4924 / 336 | 28,723,688 |

[Width](../../src/TASRNWidthPatch.h) retains insertion boundaries `0xd0` and
`0x238`, style registers 13/14, emote ID 10, gigantified flag 11, and scratch
registers 18–21 in the donor's existing frame 41. Original branch destinations
remain valid despite a changed literal-buffer instruction width later in the
31.6 function. Its complete 40-byte large header is admitted explicitly.

[Local echo](../../src/TASRNLocalEchoPatch.h) follows the actual
`LibraryTmiClient` factory 3504 binding to `onChatEvent` 35388. Its instruction
flow is unchanged after resolving string IDs. The donor now already uses a
full header, which is copied before changing only offset, size, frame 18 to 21,
and the added handler flag. Null-line and nonce joins retain their behavior;
preview exceptions resume original emission outside the protected interval.

[Composer](../../src/TASRNComposerPatch.h) retains 31.6's frame 100 and reads
draft/channel/native map from registers 51/78/49. The insertion moves to `0xad`,
immediately after the native map read at `0xa7`. Calls stage in registers
89–99, isolated from the live prefix. Only the local preview map is replaced;
the undefined register is restored and native draft, selection, props, and
send serialization are retained. Stage admission now requires the exact local
predecessor length rather than a length range.

[Popup](../../src/TASRNPopupPatch.h) and
[strip](../../src/TASRNStripPatch.h) retain factory joins `0x5e` and `0x46`,
respectively, with original frames 32 and 22 and contained installer exceptions.
[rn_graft.py](../../tools/rn_graft.py) regenerates 11 owned card functions
(1,800 bytes) and 131 owned strip functions (28,492 bytes). They begin at
function IDs 48985 and 48996; the final body has 49,127 functions. Original
literal buffers, strings and their kinds, handlers, and debug records are
preserved; function-table expansion relocates absolute section/code offsets.
Long string operands are widened where required by the 31.6 pool.

### Module bindings and changed autocomplete API

Owned requires are checked against donor registrations and writable exports:

| Adapter dependency | 31.6 Metro module |
| --- | --- |
| React / RN / NativeModules / JSX | 72 / 5 / 16 / 245 |
| Theme and sheet APIs | 2071 |
| EmoteTextInput | 3459 |
| Autocomplete leaf | 4676 |
| ChatAutocompleteTray | 4777 |
| useChatComposer | 4751 |
| Native backspace / alias barrels | 3458 / 3488 |
| EmotePickerTray | 4153 |
| ChatSettingsSheet | 4937 |

Settings module 4937 registers factory 4941, which exports component 22549.
The verifier checks that registration and rejects using the factory number as
the module number. Native composer catalog publication also moved: ChatArea
21721 assigns `emoteMap` in slot 21 at `0xa886`, not the old slot 20.
Native library row/header heights remain 52/28; the verified grid/navigation JSX
surfaces moved to `0x1957`/`0x1352` in EmotePickerTray 20260.

Payload regeneration initially refused `confirmHighlightedMatch`, which is
absent from 31.6. Donor `useAutocomplete` 21822 returns `matches`,
`forcedSelection`, `onChange`, `onMatchSelect`, and `reset`. The caller now
passes through `useComposerAutocomplete` (factory 4775/helper 22037).
[ProviderEmoteStrip.js](../../src/rn/ProviderEmoteStrip.js) removes the obsolete
confirm override. Provider filtering and stale emote-match masking remain;
current native selection/change/reset callbacks and their identities remain
intact, without adding React hook slots. Fixtures cover that returned shape.

The structural verifier caught changed dependency indices and catalog slots
while rechecking the port. Those checks were rebound to the inspected 31.6
instructions and registrations, rather than dropping the assertions.

### Port verification

- [Width/local/composer verification](../../tools/verify_rn_width.py) passes:
  34 original width branches, five local branches, and 264 composer branches
  preserve their destinations. Original instructions remain intact except the
  verified local null-branch widening; unrelated function metadata is preserved.
  Independent Hermes-98 disassembly and the Call4
  compiler probe confirm call frames and exception intervals. Same-size altered
  inputs with freshly recomputed footers are refused without input mutation.
- [Full graft verification](../../tools/verify_rn_popup.py) passes deterministic
  regeneration, module/leaf bindings, every unaffected function body/header,
  original constants/handlers/debug data, imported closure/branch/handler bounds,
  and independent disassembly. The last stage checks 48,996 predecessor
  functions, including the already admitted 11 card functions.
- [Compiled runtime validation](../../tools/validate_rn_snapshot.py) passes
  against pinned Hermes source `40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c`.
  It executes the production graft, real donor settings factory/component,
  original RN overlap/window algorithm, and native demand handler: 32 bounded
  snapshots and all 7,344 window scenarios pass. Settings checks include
  omitted/null/empty sections, first-row reload scope/close, and identity subpages.
  React/RN and Objective-C boxing use host adapters; this is not iOS execution.
- The complete host suite runs 171 tests: 170 pass, one Apple Foundation test
  is skipped on Linux. Both private donor/Hermes tests execute and pass.
  `make verify` passes both native artifact contracts; both DEB packages verify.
- The unsigned build-5 IPA passes the patcher's archive checks and a separate
  `verify_ipa.py` invocation. Its disk `index.ios.bundle` remains the original
  31.6 body: the runtime patch is not written into the IPA. Icon assets and
  `Assets.car` pass packaging preservation checks.

Compiler SHA-256:
`1f7f8e1d1cb9dc7ed6d3432c92f511fe1c47cf3d0f3a3eea8f757126752c38e5`.
Snapshot runner SHA-256:
`4e3954bf41b6083a35fd90f0ca4d34ef18d304ee3e8abeceea7d07dd28520665`.
Build-5 framework binary SHA-256:
`0bfde7d3fe484ce3d8f514722c260ae3accd907b699a77bf3a3a46f6b6829540`.

Unsigned artifact: `Twitch_31.6_Streamside_3.1.0-build.5_unsigned.ipa`,
194,477,376 bytes, SHA-256
`1f2e91afa41fe683ff4138e0f85e86abbec181d9a61546be4f06d62d5d66dd98`.

### Device and release status

The Hermes port is implemented and host-validated. Device acceptance on 31.6
is still pending for actual renderer routing, own/incoming emotes, composer
proportions and cursor continuation, holds, suggestions/library/settings,
account/channel changes, and lifecycle. The native/runtime layout and playback
limits from the inspection remain open, including an actual ad-bearing case.
The previous 31.5 device confirmations do not count as 31.6 acceptance.

No release tag or main merge is part of this trial. Public feature documentation
is reconciled at feature freeze under the maintenance policy.

### Build-5 device follow-up and build-6 cursor trial

Build 5 was reported to work on 31.6, with a remaining cursor displacement
during continued typing after an emote becomes an image. The device/iOS/signing
configuration and a full interaction matrix were not recorded. This confirms
the reported port result, not blanket acceptance of the pending cases above.

The [cursor investigation](RN_COMPOSER_CURSOR.md#build-6-follow-up-late-native-requests-on-316)
records the build-6 correction for native selection requests arriving after
newer typing. The original five-stage donor admission is retained. Build-5
artifact hashes and validation results remain attached to build 5.
