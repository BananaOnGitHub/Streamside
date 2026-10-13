# Twitch 31.6 compatibility inspection

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
