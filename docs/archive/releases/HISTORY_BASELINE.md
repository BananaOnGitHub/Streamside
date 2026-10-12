# Version history and reconstruction notes

> Historical record. Its experiment scope, pending checks, failed approaches, and donor-specific addresses refer to the builds named below, not the current implementation. Preserved from [docs/HISTORY.md at 7754dd9](https://github.com/BananaOnGitHub/Streamside/blob/7754dd9df6de077b0b5f4c4a2b98b8d738da29bf/docs/HISTORY.md). Current guide: [HISTORY.md](../../HISTORY.md). [Archive index](../README.md).

## Compatibility and diagnostic archive naming

The completed build-92 compatibility branch is renamed to
`archive/compat/twitch-31.5`. The four diagnostic archives move under
`archive/diagnostic/` with their existing names, heads and histories preserved.
Main documentation links follow the new names; `main` remains the active
3.0.0 release-preparation branch. This changes no runtime source or build number.

## 3.0.0 main consolidation — build 92 retained

Device testing confirms build 92's touch highlight works and authorizes moving the
completed work to main for 3.0.0 release preparation. Main is a direct ancestor
of compat/twitch-31.5, so the complete 51-commit compatibility history moves
across without conflicts or a runtime source change. The diagnostic archives
remain preserved; their independent forensic probes are historical work, not
additional release implementations. Release documentation now describes the
completed RN and legacy behavior. VERSION remains 3.0.0 and the tested internal
bundle version remains 3.0.0.92. No release tag or publication is part of this
consolidation.

## Twitch 31.5 RN Reload Emotes pressed highlight — build 92

Device testing confirms build 91's row works. Build 92 adds the same Pressable style
callback used by Twitch's menu row (donor functions 22113/37952): the active
background is theme.colors.backgroundElevation1, returning to transparent on
release or cancellation. React Native owns the pressed state, including holds
and scroll cancellation. The row's placement, geometry and reload action remain
unchanged; existing source/compiled fixtures also exercise both style states.

## Twitch 31.5 RN Reload Emotes main-page admission — build 91

Build 90 still omitted the row on the tested Chat Settings sheet. Its main-page
guard required a truthy containerSections value, but this optional prop may be
undefined or null. The donor always creates the prop on the main page; build 91
checks its presence and the settings/onRequestClose signature instead. Reload
Emotes is now the first scroll row, below the sheet title and before Identity,
so it is visible without scrolling through the preferences.

The required Hermes validation now executes the unchanged donor settings factory
4884 and component 22114 together with the compiled production adapter, rather
than checking only a hand-built page. The old guard reproduced the missing row
with omitted sections. The corrected adapter passes omitted, null and empty
sections, preserves donor scroll behavior, reloads the explicit channel, closes
the sheet, and leaves the donor's own identity subpage unchanged. Shared fixtures
also retain hidden/disabled and channel-change checks. The device-confirmed
unconfirmed-input guard and native reload implementation are unchanged.

## Twitch 31.5 RN Reload Emotes module binding — build 90

Device testing confirms build 89's unconfirmed-input guard works, but its RN reload
button does not appear. The adapter used Hermes factory function ID 4884 as a
Metro module ID. The exact donor's global __d call registers that factory as
module 4880; the incorrectly imported module has no ChatSettingsSheet export.
Build 90 corrects only this binding, leaving the confirmed native guard intact.

The prior host mock placed the settings export at the same incorrect ID, so its
source/compiled button tests could pass without attaching to Twitch's real UI.
The mock now maps settings to 4880 and gives 4884 no sheet export. The required
Hermes validation also parses the admitted donor's actual __d registration and
the factory's writable ChatSettingsSheet export (component function 22114), then
compares that module ID with the owned adapter. A regression explicitly refuses
the erroneous 4884 binding before compiled validation/build admission.

## Twitch 31.5 RN settings reload and provisional input — build 89

Build 89 prepared a Reload Emotes row for the RN ChatSettingsSheet main page;
the failed module binding is corrected in build 90 above.
The owned wrapper preserves the native sheet and scroll props, appends a themed
accessible row, requests a refresh for that sheet's explicit channel, and closes
the sheet. The native bridge rejects disabled, unknown and ambiguous channels.
The existing refresh retires old identities, clears provider generations, and
refetches global and selected-channel catalogs; background last-room state cannot
redirect the RN action. Subpages and other scroll views retain their original UI.

The donor change delegate tests markedTextRange, but its value and emote-map
prop setters can rebuild attachments during unconfirmed keyboard composition.
Build 89 holds provisional delegate events and guards both setters before their
original implementations. Provisional draft values are discarded; only the latest
recognition map is retained per input and applied after native committed-text
reconstruction. Cancelling a prediction cannot replay its full suggested value.
UIKit retains its composition, and confirmed input uses Twitch's tokenizer.
The diagnostic report adds map-hook availability and an aggregate hold counter.

ASAN/UBSAN native regressions cover commit/cancellation, deferred-map replacement
and clearing, explicit reload scope, refusal, catalog retirement and fetches.
Shared source and compiled Hermes fixtures cover the RN button, native props,
subpages, hidden/disabled presses and channel changes. Full host/build/package
checks are required; actual iOS inline-prediction and IME behavior remain a
focused device trial.

## Twitch 31.5 third-party library labels — build 88

The RN library now shows each third-party emote's name below its thumbnail,
including its provider Recent row. Labels use the suggestions picker's
11-point secondary text styling and a single-line, trailing ellipsis. Full
names remain available to accessibility and are inserted unchanged. A fixed
32-point thumbnail band keeps labels aligned across emote aspect ratios.

The existing 52-point tiles, five-row/260-point library, horizontal column
metrics, virtualization settings, image identities and transport scheduler are
unchanged. The legacy library already displays names and is left unchanged.
Host library regressions and the compiled Hermes fixture cover label content,
geometry and styling; the host test also covers long/Unicode names and exact
insertion. These fixtures do not claim on-device visual confirmation.

## Twitch 31.5 diagnostic closure — build 87

`compat/twitch-31.5` advances from build 72 to build 87 by fast-forward. Builds
73–78 investigate and correct RN fractional-column startup demand; builds 79–82
add bounded cache-first delivery, real Foundation validation and conservative
network receipt metadata; build 83 adds bounded overflow recovery. Builds 84–87
investigate and correct native Recent startup and footer tint/insertion in the
legacy picker. Device testing confirmed the build-86 and build-87 legacy fixes.

All four diagnostic branch histories are preserved under `archive/`, with
documentation-only closure commits. Only the image-demand implementation line
is brought into compat; the older independent probe histories remain separate.
The source stays build 87, main is unchanged, and no release is published.
See [the archive index](https://github.com/BananaOnGitHub/Streamside/blob/7754dd9df6de077b0b5f4c4a2b98b8d738da29bf/docs/DIAGNOSTIC_BRANCH_ARCHIVE.md) for precise heads,
validation limits and the decision to freeze performance architecture.

## Historical reconstruction

This project began as a practical patch for a decrypted Twitch 30.4.2 arm64
app and gained dedicated packaging and patching tooling in 2.0.3.

The early source downloads were not all retained. Their history was recovered
from surviving source archives and the injected Mach-O dylibs in the original
test IPAs. The table distinguishes exact source from reconstructed source so
the Git history does not pretend to have evidence that no longer exists.

| Version | Date | Architecture | Source confidence | What changed |
| --- | --- | --- | --- | --- |
| 1.0.0 | 2026-08-12 | video-swap-new 1.55 / solution 23 | Exact surviving archive | Initial native iOS port. |
| 1.0.0 signing correction | 2026-08-12 | video-swap-new | Exact surviving artifact | Replaced the downloadable dylib with an ad-hoc-signed build; no source delta. |
| 1.0.1 | 2026-08-12 | video-swap-new | Exact reconstruction | Added a 64 KiB signature reservation. Applying the recovered reservation tool to the 1.0.0 dylib produces the IPA dylib byte-for-byte. |
| 2.0.0 | 2026-08-12 | VAFT solution 24 | Source-level reconstruction | First VAFT port. Recovered by reversing the small 2.0.0-to-2.0.1 native delta from symbols and arm64 code. Formatting and comments may differ from the lost original source. |
| 2.0.1 | 2026-08-12 | VAFT solution 24 | Exact code state | Added direct playback-token request normalization. Its dylib is byte-identical to the one built from the surviving 2.0.2 source archive. |
| 2.0.2 | 2026-08-12 | VAFT solution 24 | Exact surviving archive | Packaging-only fix: restored the complete Twitch `Assets.car`; native code is byte-identical to 2.0.1. |
| 2.0.3 | 2026-08-18 | VAFT solution 24 | Exact surviving archive | Isolated VAFT state per stream to fix PiP/profile-preview cross-talk. Added the local patcher and tests. |
| 2.1.0 | 2026-08-18 | VAFT solution 24 | Current source | Renamed the dylib/load command and added standalone rootful/rootless DEBs. |
| 2.2.0 | 2026-08-21 | VAFT solution 24 | Surviving source | Added the in-app settings/diagnostics system and restored the proven framework-based sideload compatibility identity while retaining the clean jailbreak identity. |
| 2.2.1 IPA | 2026-09-28 | VAFT solution 24 | Device-tested binary and exact-input patch script; newer diagnostics source unavailable | Adds R5 opt-in privacy and route diagnostics, clearer copy, and a main Settings button guard. |
| 2.2.1-jb | 2026-09-28 | VAFT solution 24 | Current source, not device-tested | Packages the main Settings button fix for rootful/rootless jailbreaks. Retains 2.2.0 diagnostics, without R5 route history and labels. |
| 2.2.1 replacement | 2026-09-28 | VAFT solution 24 | Reconstructed, checked-in source; not device-tested | Replaces both release assets from one source tree with R5 privacy labels, route history, and the Settings guard. |
| 2.3.0-dev.1 | 2026-09-29 | VAFT solution 24 plus optional emotes | Development source; not device-tested | Adds bounded 7TV, BTTV, and FFZ chat emote support, a relaunch-gated switch, cache clearing, and chat-menu reload to the shared IPA/jailbreak source. |
| 2.3.0-dev.2 | 2026-09-29 | VAFT solution 24 plus optional emotes | Development source; awaits device retest | Adds emote transport/provider and chat-menu counters, hooks inherited WebSocket receive implementations, and recognizes ChatSettingsController sheets without relying on the exact title. |
| 2.3.0-dev.3 | 2026-09-29 | VAFT solution 24 plus optional emotes | Development source; awaits device retest | Instruments image response outcomes and the chat settings button/presentation path after dev.2 confirmed frame and URL rewriting but no menu hook activity. |

| 2.3.0-dev.4 | 2026-09-29 | VAFT solution 24 plus optional emotes | Exact development source | Added provider image outcomes and native chat-menu tracing. |
| 2.3.0-dev.5 | 2026-09-29 | VAFT solution 24 plus optional emotes | Incoming emotes device-confirmed | Added punctuation matching and an initial chat-menu reload button. |
| 2.3.0-dev.6 | 2026-09-30 | VAFT solution 24 plus optional emotes | Menu row device-confirmed; new emote UI failed | Added proportions, local tokenizer hook, and provider detail sheets. Diagnostics showed zero local calls, sizing adjustments, and tap hits. |
| 2.3.0-dev.7 | 2026-09-30 | VAFT solution 24 plus optional emotes | Provider tap details device-confirmed; spacing corrected but images stay square | Corrects token-object lookup and TextKit spacing. Local-message filtering rejects NSNumber sender IDs, so own messages remain text. |
| 2.3.0-dev.8 | 2026-09-30 | VAFT solution 24 plus optional emotes | Exact development source; device-confirmed | Accepts NSNumber sender IDs and corrects separate provider image-layer frames, with scoped layout recovery and counters. |
| 2.3.0 | 2026-09-30 | VAFT solution 24 plus optional emotes | Exact checked-in source; final IPA packaging differs from working dev.8 | Finalizes emotes; later loader investigation found lost segment normalization in the packaged framework, despite the same main executable. |
| 3.0.0 prepared | 2026-09-30 | Streamside; VAFT solution 24 plus emotes | Publication held; composer/keyboard device test pending | Project/app rebrand, minimal suggestions, editor previews, provider/scope keyboard tab and native Recent integration. Logo pending. |
| 2.3.1 prepared | 2026-09-30 | VAFT solution 24 plus optional emotes | Source-built loader device-confirmed; publication held for approval | Removes the active donor identity in favor of Streamside; enforces 16 KiB geometry, signing metadata, and build-to-package fingerprints. Launches on device. Candidate build 2 raises the provider response/registry limits after live 7TV sets exposed the old 2 MiB rejection; emote fix awaits device verification. |

## Binary evidence

All historical test IPAs used the same Twitch 30.4.2 main executable. Only the
injected dylib changed between native revisions; 2.0.0 through 2.0.2 also
exposed the asset-catalog packaging regression described below.

| Version | Injected dylib SHA-256 | `LC_CODE_SIGNATURE` reservation |
| --- | --- | --- |
| 1.0.1 | `f561350754e84062ecdf90cf1d47bf14b21f05852d7a4aa0f4d5f2c1a04c425f` | 65,536 bytes |
| 2.0.0 | `f329fea631d6a74e866ab8de4a2bef1af3e2ee948a2f292789a77aba55fe3332` | 65,536 bytes |
| 2.0.1 | `61a50c69c86a020c0855411db85aaaebae3cb5a0bc8237f71ed454201d6abf86` | 65,536 bytes |
| 2.0.2 | `61a50c69c86a020c0855411db85aaaebae3cb5a0bc8237f71ed454201d6abf86` | 65,536 bytes |
| 2.0.3 | `7c55a15000fb1b8dcab436aba05c1a952618bf67af1e165a83914577c61048ac` | 65,536 bytes |

The only native symbols added by 2.0.1 were the GraphQL request-normalization
helpers, the two `NSURLSession` data-task replacements, and their stored
original implementations. The 2.0.1 and 2.0.2 dylibs are identical. The only
IPA entry changed by the 2.0.2 repack was `Assets.car`, restoring the same CRC
present in the working 1.0.1 and 2.0.3 packages.

## Architecture transition

Versions 1.x followed `video-swap-new`: detect ad-bearing playlists, request
alternate player types, and swap to a clean rendition. Version 2.0.0 moved to
VAFT's broader stitched marker, ordered alternate-master cache, closest
rendition fallback, and blank-segment response. Version 2.0.3 retained VAFT but
replaced its single global stream state with per-channel contexts required by
Twitch mobile's simultaneous PiP and muted profile-preview players.

The early `Tweach.dylib` name was a donor compatibility shim: the Twitch
executable already had that load command. Version 2.1.0 introduced the clean
`@rpath/TwitchAdBlock.dylib` identity used by the standalone jailbreak packages.
Testing showed that common sideload resigners rejected the same library after a
filename/load-command change and also rejected the initial replacement dylib's
Mach-O layout. Version 2.2.0 keeps the clean identity for jailbreaks and uses
the donor-compatible `Tweach.framework/Tweach` identity with 16 KiB-aligned
segments for sideloaded IPAs.

The 2.3.0 loader investigation corrected that earlier inference: all three
failed rename/path trials inherited the final IPA's unnormalized framework.
Working dev.8 used rounded segment ranges, while the final IPA had `__TEXT`
size 123528 instead of 131072 and `__DATA_CONST` size 40 instead of 16384.
Restoring the build's normalizer and compact signature reproduced the aligned
source-built 2.3.0 framework exactly. The corrected migration trial launches.
The current build uses Streamside and binds normalization to each package's
actual bytes; historical names below and the archived R5 reproducer are retained
only for provenance and migration of old inputs, never as an active loader.
