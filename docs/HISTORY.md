# History

This history follows release and build order. Commit/report links provide provenance; dates are left to those records. Public release changes are summarized separately in [Changelog](../CHANGELOG.md).

“Host checks” means automated behavior under controlled adapters. “Donor checks” means structural analysis of the inspected binary/bundle. “Device confirmation” means the visible result actually recorded for that configuration. Missing evidence stays missing.

## Early releases and source recovery

The repository history was reconstructed from surviving source archives and injected binaries. Some commits record recovered states rather than original development commits.

| Version/state | Change and evidence | Source reference |
| --- | --- | --- |
| 1.0.0 | Native video-swap-new 1.55 / solution 23. The original source archive survives. | [e504a6a](https://github.com/BananaOnGitHub/Streamside/commit/e504a6a) |
| 1.0.0 signing correction | Added ad-hoc signing/header padding to the downloadable binary without changing the ad-blocking source. | [47f7928](https://github.com/BananaOnGitHub/Streamside/commit/47f7928) |
| 1.0.1 | Expanded replaceable signature space to 64 KiB. The recovered reservation step reproduces the surviving IPA dylib byte-for-byte. | [7b433d3](https://github.com/BananaOnGitHub/Streamside/commit/7b433d3) |
| 2.0.0 | Transitioned to VAFT solution 24. The original source archive was lost; behavior was reconstructed from the later exact source state, symbols, and arm64 delta. Formatting/comments are not claimed original. | [61efb62](https://github.com/BananaOnGitHub/Streamside/commit/61efb62) |
| 2.0.1 | Added direct playback-token task normalization while preserving unrelated authenticated startup requests. Its native binary is identical to the surviving 2.0.2 binary. | [1f22a0a](https://github.com/BananaOnGitHub/Streamside/commit/1f22a0a) |
| 2.0.2 | Packaging-only complete Assets.car restoration fixed signed-in scene creation; native source/binary remained the 2.0.1 state. | [96b6713](https://github.com/BananaOnGitHub/Streamside/commit/96b6713) |
| 2.0.3 | Replaced global playback state with per-channel contexts and exact rendition ownership, fixing PiP/profile-preview substitution. Complete source archive survives. | [ac71ae1](https://github.com/BananaOnGitHub/Streamside/commit/ac71ae1) |
| 2.1.0 | Standalone clean dylib identity, rootful/rootless packaging, reproducible tooling, Apache-2.0, and CI. Published as a jailbreak prerelease, not a standard IPA release. | [8f13c1f](https://github.com/BananaOnGitHub/Streamside/commit/8f13c1f) |
| 2.2.0 | Native settings/diagnostics and signer-compatible framework geometry. Retained historical donor path for IPA and clean identity for jailbreak. | [8c8b543](https://github.com/BananaOnGitHub/Streamside/commit/8c8b543) |

Surviving dylib evidence:

| Version | SHA-256 | Signature reservation |
| --- | --- | --- |
| 1.0.1 | `f561350754e84062ecdf90cf1d47bf14b21f05852d7a4aa0f4d5f2c1a04c425f` | 65,536 bytes |
| 2.0.0 | `f329fea631d6a74e866ab8de4a2bef1af3e2ee948a2f292789a77aba55fe3332` | 65,536 bytes |
| 2.0.1 / 2.0.2 | `61a50c69c86a020c0855411db85aaaebae3cb5a0bc8237f71ed454201d6abf86` | 65,536 bytes |
| 2.0.3 | `7c55a15000fb1b8dcab436aba05c1a952618bf67af1e165a83914577c61048ac` | 65,536 bytes |

Historical IPAs used the same Twitch 30.4.2 main executable. The 2.0.2 repack changed Assets.car rather than the dylib. These binary identities do not validate later repackaged assets.

## 2.2.1: binary staging, correction, and source parity

The R5 binary-staging line added temporary diagnostic labels and route history while its newer original source was unavailable. It also exposed a settings-entry scope problem: the button could appear on Chat Identity.

R6's tighter guard removed the entry entirely. R7 restored it only on main Settings and was device-confirmed. The exact-input historical staging script and binary hashes survive in [R5 production staging](archive/releases/R5_PRODUCTION_STAGE.md).

The initial IPA and initial jailbreak source did not contain identical diagnostics. The replacement line reconstructed the R5 behavior in checked-in source and rebuilt both formats. [89f46da](https://github.com/BananaOnGitHub/Streamside/commit/89f46da) restored the shared implementation; [56255e2](https://github.com/BananaOnGitHub/Streamside/commit/56255e2) aligned provenance with replacement assets.

The original binary-staged result was device-tested; the source-backed replacement passed build/package checks without a recorded replacement-device acceptance. The current published 2.2.1 IPA has SHA-256 `c930d39a28c9abf4a6d4e5fb8f042b84c58f648c5c31a3ee3ff5172e3d3e1d6a`. The candidate hash in [the archived release note](archive/releases/RELEASE_2.2.1.md) is a different artifact and remains preserved.

## 2.3.0 development and publication

| Build | Attempt, correction, or observed result |
| --- | --- |
| dev.1 | Added optional bounded 7TV/BTTV/FFZ definitions, incoming metadata, enable/clear/reload controls. Initial device validation was pending. |
| dev.2 | Added inherited receive coverage and aggregate provider/menu diagnostics. Frame/URL rewriting was observed, but the menu seam remained absent. |
| dev.3 | Added image and native menu tracing to separate successful matching from UI delivery. |
| dev.4 | Added provider response outcomes and native presentation tracing; no visible-success claim followed from counters alone. |
| dev.5 | Punctuation matching and native action-sheet placement made incoming emotes/menu behavior observable on device. |
| dev.6 | Initial proportional/local/detail work failed at native seams: no local callback, effective sizing, or tap hits despite incoming images. The scrolling reload row was confirmed. |
| dev.7 | Correct token-object ID lookup and TextKit reservation enabled provider details/spacing. The bitmap still stayed square; NSNumber sender IDs were still rejected. |
| dev.8 | Accepted NSNumber sender IDs and corrected the separate image-layer frame. Incoming, sent, wide/animated emotes and details were device-confirmed on 30.4.2. |
| 2.3.0 | Public IPA and separate jailbreak prerelease. Final IPA packaging differed from the working development framework. |

[The preserved development changelog](archive/releases/DEVELOPMENT_CHANGELOG.md) retains the original scope/counters and intermediate pending states. Publication occurred at [9e8bfb7](https://github.com/BananaOnGitHub/Streamside/commit/9e8bfb7); release notes describe the historical iPhone 16 Pro / iOS 18.2 feature baseline.

## The unpublished 2.3.1 transition

The final 2.3.0 framework lost segment normalization. Its main executable still matched working dev.8, so three rename/path trials inherited the same bad framework and incorrectly implicated the loader name.

Working dev.8 used rounded segment ranges. The failed final framework had __TEXT size 123,528 instead of 131,072 and __DATA_CONST size 40 instead of 16,384. Restoring normalization and compact signing reproduced the aligned source-built framework; the corrected Streamside-identity migration launched on device.

[2601ad2](https://github.com/BananaOnGitHub/Streamside/commit/2601ad2) made build-to-package fingerprints/layout/signature checks mandatory. Prepared 2.3.1.2 at [f9bc46b](https://github.com/BananaOnGitHub/Streamside/commit/f9bc46b) raised provider response admission to 8 MiB and room capacity to 4,000 after valid large 7TV bodies exceeded the older 2 MiB limit.

2.3.1 was prepared, not published. These changes continue in 3.0.0; they are not separate public releases.

## Early 3.0.0 composer and native catalog work

[545651a](https://github.com/BananaOnGitHub/Streamside/commit/545651a) introduced the Streamside composer/provider keyboard direction. Subsequent commits corrected undo-manager exceptions, hit regions/text styling, scene-window touch routing, active-word preview timing, UIKit autocorrection ownership, drag cancellation, native catalog bridging, selector suppression, and frozen-on-open recents.

The surviving records do not individually identify every numbered build 2–16. These changes are linked by source history rather than assigned invented labels. Native catalog work found private Swift publication paths bypassing ObjC wrappers, a Swift weak input delegate, and the need to preserve actual array/string/URL ownership.

Presentation-only suppression corrected native table crashes: zero returned rows conflicted with Twitch's scroll-to-row-zero behavior, and a UIView wrapper could not accept table-only reload calls. These were implementation failures, not provider API failures.

Stable scope/name/URL IDs corrected cross-launch image mismatch. Separate decoder ownership corrected composer/suggestion animation interference.

## Builds 17–38: UIKit interaction and animation

| Build | Source | Change and recorded outcome |
| --- | --- | --- |
| 17 | `3cd5764` | Provider Recent row beneath Frequently Used; retained native history. |
| 18 | `8351d72` | Clip provider Recent beneath the pinned heading. |
| 19 | `82b48df` | Restore provider footer entry after native stack replacement. |
| 20 | `e793677` | Embed provider library between native sections. |
| 21 | `3fa30e2` | Invalidate native cached metrics before placement; still insufficient as the sole gap mechanism. |
| 22 | `36f197c` | Copied layout coordinates/content/visible-query translation reserved the gap; device spacing confirmed. |
| 23 | `6d8bbde` | Five-row horizontal library; device layout confirmed. |
| 24 | `12db7be` | Case-insensitive display ordering; exact lookup unchanged, device order confirmed. |
| 25 | `753a0d7` | Cancellable asynchronous transport and reused metadata snapshots; playback-pause improvement observed. |
| 26 | `37d6d79` | Contiguous substring suggestions; device matching confirmed. |
| 27 | `5f412e4` | Immediate preview reservation and unified menu backspace; device behavior confirmed. |
| 28 | `681c16b` | Transparent loading pixel; device placeholder behavior confirmed. |
| 29 | `3caf909` | Wait for native Recent heading/layout before gap placement; device initial layout confirmed. |
| 30 | `29f1a23` | Attachment-local composer GIF clocks; animation observed, later ownership interference corrected. |
| 31 | `e22353b` | Isolate preview decoders from suggestion-image playback. |
| 32 | `b26674a` | Scroll-only footer-selection ownership; device testing rejected it as insufficient. |
| 33 | `6387c54` | Guard renderer-boundary native footer paints while provider selection owns the section. |
| 34 | `6a7b483` | Shared provider details from library/editor holds. |
| 35 | `d5f281e` | Match 0.5-second hold timing and keep suggestions below modal sheets; device behavior confirmed. |
| 36 | `a3c7293` | Gesture priority and one successful-presentation haptic; device single haptic confirmed. |
| 37 | `09c82a3` | Wait for owned sheet dismissal before browser launch; device browser-return behavior confirmed. |
| 38 | `ffd0aca` | Weak visible provider-layer recovery and preserved long GIF delays; host coverage recorded, isolated final device acceptance not established by the candidate entry. |

The [native-emote archive](archive/investigations/NATIVE_EMOTES.md) and [development diary](archive/releases/DEVELOPMENT_CHANGELOG.md) retain full ownership, geometry, gesture, timing, and native-symbol findings.

## Builds 39–47: image and playback forensics

Build 39 (`8df9289`) added opt-in target-code diagnostics for emotes that remained text. Build 40 (`cc1299a`) separated provider-image delivery from HLS completion work, then exposed an expired room string in an asynchronous BTTV callback. Build 41 (`2626814`) explicitly retained that string across completion/cancellation/stale/unavailable paths.

Build 42 (`2f1e132`) sampled selected provider playback; build 43 (`70b9d21`) added retrospective visible histories; build 44 (`d39f44e`) corrected attachment child roles, capacity/eviction interpretation, and independent last-progress records.

Build 45 source at `5a0cda0` reconstructs decode/native-handoff provenance. It is not presented as a recovered original source archive. Build 73 later independently reproduced its framework byte-for-byte, a stronger but distinct artifact claim.

Build 46 (`b074e6f`) added weak result/raster construction/reuse evidence. Build 47 (`1f58c73`) added guarded requester/cache-decision observations. Reuse of the same observed static UIImage did not establish a cache hit, nor did a prior matching GIF attempt prove flattening. Direct Swift/unobserved/expired paths remained gaps.

These independent probe branches were not merged wholesale into the release implementation. [Their records](archive/README.md#archived-branches) preserve purpose, outcome, and coverage limits.

## Builds 48–54: Twitch 31.5 and the RN boundary

| Build | Source | Investigation/result |
| --- | --- | --- |
| 48 | `5472354` | Non-diagnostic 31.5 donor/package trial; exact app/UUID/input metadata preserved. |
| 49 | `c4243ef` | Removed obsolete constraints and found the missing old own-message delivery/constructor seam. |
| 50 | `3fbfa44` | Native per-message definition enrichment for the legacy renderer. This did not establish RN rendering. |
| 51 | `79013c4` | Passive RN ingress probe after legacy hooks stayed idle on the tested surface. |
| 52 | `494d375` | Bridgeless RN/Fabric surfaces and native input handoffs. |
| 53 | `423858b` | Catalog identities and metadata consumers; reports retained in RN_BUILD53_FINDINGS. |
| 54 | `572f1fa` | Paragraph/attachment consumers and presentation-seam research; standalone toolchain blocker and missing live per-emote join remained explicit. |

Reports established SRWebSocket → RCTWebSocketModule → JS ingress and TwitchEmoteInputView catalog delivery. Static tracing linked code/ID maps, IRC ranges, EmotePart, and image URL construction.

The distinctive presentation finding was that paragraph NSTextAttachment instances were reconstructed inline-child placeholders, not stable decoded-emote containers. Width had to agree with Fabric's measured child subtree. [The RN research records](archive/README.md#rn-boundary-research) preserve this, including what passive tracing did not prove.

## Builds 55–70: completed RN integration

| Build | Source | Attempt, correction, and evidence |
| --- | --- | --- |
| 55 | `4b137ab` | Incoming-only synthetic IRC metadata. Reports B/C established observed static/animated rendering and animation after scrolling; geometry remained square. |
| 56 | `1fbb124` | Exact-body wrapper/image width patch before Fabric measurement; tested proportional reception confirmed. |
| 57 | `2e8e4e6` | Separate TmiClient local-echo patch registered/admitted but recorded no local callbacks; sent code stayed literal. |
| 58 | `d2fd744` | Corrected NativeModules lookup, but callback/export counts still stayed zero on the tested send. |
| 59 | `804aa75` | Moved to LibraryTmiClient ordinary-chat event; reached export discovery, but sent messages disappeared before native preview entry. |
| 60 | `c58afe5` | Frame 21 and isolated preview catch corrected the failure; tested sent messages/emotes rendered. |
| 61 | `ea8654f` | Scoped native input recognition map; device trial produced a placeholder without an image. |
| 62 | `4f64a58` | Covered native URL-based image completion transport; images appeared but were square/static. |
| 63 | `a588e02` | Native provider attachment width and bounded GIF clocks; width worked, first-download animation missed startup. |
| 64 | `59b3682` | Track pending input before decoder creation; first-download GIF startup confirmed. |
| 65 | `82c3251` | Independent passive provider tap/sheet trace: route reached the RN sheet, query-backed native content remained absent. |
| 66 | `c8c4842` | Provider card inside the existing bottom sheet; device popup confirmed. |
| 67 | `e4ede56` | Compact provider suggestion strip; device behavior confirmed. |
| 68 | `3593a6c` | Native Twitch/subscriber catalog in unified suggestions and conditional autocomplete takeover; confirmed before the library port. |
| 69 | `8285854` | RN tray provider section and frozen recents; device library confirmed. |
| 70 | `7d0c3ec` | Controls, five-row browsing, native token backspace; layout confirmed, slow image loading then reported. |

### The build-59 call-frame failure

Frame 18 staged outgoing Call4 values over the still-live callee register. Valid disassembly and a simplified host interpreter had not modeled that sequential order. The TypeError occurred before native entry and original emission.

Build 60 moved outgoing slots above live locals, added failure injection across preview lookup/call/write, and resumed original emitLine on added-preview exceptions only. Its record reports 71 passing host tests, donor metadata/branch checks, independent Hermes disassembly, and package verification. Device confirmation is a separate result.

The separate /me handler stayed unchanged. [Local-display trial](archive/experiments/RN_LOCAL_ECHO_TRIAL.md) retains the exact registers, headers, and artifact evidence.

## Builds 71–78: demand, failed probes, and fractional geometry

Build 71 (`991b7aa`) introduced shared provider caching/coalescing. Its report showed cancellation churn and slow completions. Build 72 (`645d34f`) kept bounded detached active transfers through view recycling, dropped abandoned queued work, and reserved foreground admission.

Build 73 (`58b82e3`) reconstructed demand observations; build 74 (`c4f4446`) separated masks/ranges, lifecycle, assets, and flights. Reports established full-catalog stationary startup demand, not merely a high cumulative load count.

Build 75 (`863cc25`) attempted calculation capture but emitted no accepted rows. Build 76 (`3e67fbb`) added stage accounting and compiled validation, corrected a literal-kind/parser mismatch, and still encountered a throwing nested helper. Neither diagnostic failure itself explained the render defect.

Build 77 (`9ad8373`) independently guarded base values/helper failures and accepted all 16 startup rows. The range grew 0..6 → 0..13 → 0..20 toward all 168 columns. Metric queries appeared valid within the recorded tolerance.

Actual donor overlap/window execution reproduced the gap at fractional column endpoints: 739.9999999999999 versus 740. The undefined overscan end fell back to the last item and spent another seven-item batch expanding each time.

Build 78 (`4c24b7d`) derived interval length from adjacent offsets without changing RN's algorithm or transport capacities. Stationary opening/reopening stabilized at 0..11 and 60 live JS image instances in the recorded catalog; scrolling peaked at a 26-column mask/130 instances.

The maintained baseline at `8e32a28` covers 1,584 compiled window calculations, logical identities, and native snapshot acceptance. Those are not physical-view/device-animation tests. [Calculation record](archive/investigations/EMOTE_DEMAND_PHASE1B_CALCULATION.md) preserves the failed capture, literal-kind correction, throwing helper, numerical defect, and observed cleanup.

## Builds 79–83: cache annotation and bounded recovery

| Build | Source | Result/correction |
| --- | --- | --- |
| 79 | `2f2c7d1` | Separate cache-first lookup lane. Initial Apple candidates failed due to compilation/run-loop/delegate-task integration; later real Foundation cache/revalidation passed at `80f14f6`. Device proposals still yielded zero annotations. |
| 80 investigation | `839a02f` | First-rejection counters and production annotation tests isolated missing Date. The committed bundle/report labels still say build 79; do not silently relabel the artifact. |
| 81 | `149e87f` | Passive accessor/dictionary comparison confirmed Date/Expires absence through both APIs on the recorded responses. |
| 82 | `7b32f49` | Network-proven original receipts for eligible Date-less entries; local-cache reuse cannot mint/renew a receipt. |
| 83 | `a3e107a` | Independent bounded overflow recovery with original deadlines, cancellation, and normal scheduler ownership; no throughput increase. |

Build-82 E→F added 197 direct hits and 18 Foundation tasks, all local-cache transactions, with additional queue waits at most 250 ms. This establishes effective warm reuse for that run, not universal latency or proof that earlier long queues were harmless.

[Cache record](archive/investigations/EMOTE_CACHE_PHASE2.md) and [overflow record](archive/experiments/EMOTE_OVERFLOW_RECOVERY.md) retain failed candidates, callback evidence, rejection accounting, and saturation limits.

## Builds 84–87: retained legacy picker

Build 84 (`762eb2e`) tried deferred layout settlement for initially blank native Recent and passed a host ordering fixture, but did not fix the device symptom. Build 85 (`2755acc`) added bounded passive palette observations.

The device trace found zero sections at bind with an already inserted 410-point section-zero gap. When native sections arrived, translated query geometry could exclude the header/cells needed to classify placement. Build 86 (`144a8e1`) deferred the gap until native publication and fixed first-opening Recent.

Build 87 (`7f48f67`) restored the owned footer's inactive tint at handoff and bound the palette container before lazy footer creation, resolving a weak input owner after keyboard reparenting. It repaired insertion during dragging without another timer/reload/synthetic scroll. Both fixes were device-confirmed.

The recorded build-87 host suite had 117 tests with one local Apple-only skip; mandatory donor/Hermes, artifact/IPA checks and both CI jobs passed. These are that build's results, not a claim about a newly run test suite.

## Builds 88–92: final RN refinements

| Build | Source | Result/correction |
| --- | --- | --- |
| 88 | `5a6fa73` | Names below provider library/Recent thumbnails, preserving 52-point/five-row geometry. Subsequent device checks confirmed labels. |
| 89 | `525e555` | Guard provisional native input callbacks/value/map props; device guard worked. First reload wrapper did not appear. |
| 90 | `13f3d7f` | Correct module 4880 versus factory 4884 binding. The earlier mock shared the same error. The row still failed the device main-page guard. |
| 91 | `fa413a0` | Admit containerSections prop presence even if undefined/null; execute the real donor settings factory/component. First-row placement confirmed. |
| 92 | `30b9a14` | Native themed Pressable highlight for touch/hold/release; confirmed on device. |

The composition guard discards provisional values and retains only the latest map until native committed-text reconstruction. The menu corrections are separate: registration, page admission, then touch feedback.

## Consolidation and archives

[98e96bf](https://github.com/BananaOnGitHub/Streamside/commit/98e96bf) consolidated the completed compatibility history onto main without a runtime change or new build number. [7754dd9](https://github.com/BananaOnGitHub/Streamside/commit/7754dd9) updated archive naming.

The preserved compatibility head is `30b9a1445cb2ec04613547713787e809ae1be2cc` at [archive/compat/twitch-31.5](https://github.com/BananaOnGitHub/Streamside/tree/archive/compat/twitch-31.5). Four diagnostic branches retain independent histories under archive/diagnostic. Their [index](archive/README.md#archived-branches) distinguishes implementation heads from documentation-only closure heads.

Public version remains 3.0.0; internal bundle remains 3.0.0.92. Consolidation and documentation do not publish a release.

## Remaining provenance limits

Early numbered 3.0.0 builds 2–16 are not individually established by the inspected report/bundle labels. Build-80 investigation numbering differs from its committed label. Original and replacement 2.2.1 assets are distinct. Build-45 reconstructed source and build-73 byte-identical reproduction remain separate claims.

Where reports/artifacts cannot resolve a mapping, retain the uncertainty instead of inventing an unobserved build or device pass.

[Research archive](archive/README.md) · [Public changelog](../CHANGELOG.md) · [Current architecture](ARCHITECTURE.md)
