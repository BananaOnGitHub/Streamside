# Diagnostic branch closure — Twitch 31.5, build 87

The diagnostic investigations are closed at the user's request. Active work
continues on `compat/twitch-31.5`. It fast-forwards from build 72 to the complete
build-87 implementation and this documentation-only closure. No merge commit,
source rewrite, artificial build bump or release publication is needed.
`main` and the pre-existing archive branches are unchanged.

The archive branches retain the original histories plus documentation-only
closure commits. Their report/bundle versions remain 46, 47, 65 and 87
respectively. The active `diagnostic/` refs are removed after their archives
exist and compat contains all of the image-demand implementation work.

| Former diagnostic branch | Preserved branch | Last implementation/probe head | Disposition |
| --- | --- | --- | --- |
| `diagnostic/build46-image-result` | [`archive/build46-image-result`](https://github.com/BananaOnGitHub/Streamside/tree/archive/build46-image-result) | `b074e6f0c6e17771a64783deb70eb8baebe38c27` / build 46 | Separate legacy image-construction forensic history; not merged into compat. |
| `diagnostic/build47-request-decision` | [`archive/build47-request-decision`](https://github.com/BananaOnGitHub/Streamside/tree/archive/build47-request-decision) | `1f58c73fd36a28e72e71994e184eb495d8a05c67` / build 47 | Extends build 46 with guarded native request/cache-decision observations; not merged into compat. |
| `diagnostic/rn-chat-boundary` | [`archive/rn-chat-boundary`](https://github.com/BananaOnGitHub/Streamside/tree/archive/rn-chat-boundary) | `82c3251ffc895ecb3d4f769b61ac13d322895afc` / build 65 | Passive RN ingress, representation, presentation and info-sheet investigation; independent probes retained only here. |
| `diagnostic/rn-image-demand` | [`archive/rn-image-demand`](https://github.com/BananaOnGitHub/Streamside/tree/archive/rn-image-demand) | `7f48f67ea9ee3273f6c312587fafac6e077b10ec` / build 87 | All implementation and regression work incorporated by compat fast-forward. |

## Build 46 image-result investigation

Purpose: explain why animated provider emotes could reach legacy chat as a
still image despite an observed multi-frame GIF decode. Build 46 followed the
build-39–45 missing-emote, transport, playback and decode-provenance work.

Added guarded UIImage/CGImage and native response-wrapper observations,
donor-UUID/return-site classification, bounded weak result/raster identities,
poster relationships and a separate result-origin history. Arguments, original
results and native request/decoder selection remain unchanged. The recorder
does not retain image bodies, bitmaps or animations.

The subsequent build-47 record reports repeated assignment of the same observed
static UIImage; a later WebP response was not linked to that older object.
This establishes observed reuse, not a proven cache hit or a completed animation
fix. Direct Swift cache paths and unobserved/expired constructors remain gaps.
See the archived [branch closure](https://github.com/BananaOnGitHub/Streamside/blob/archive/build46-image-result/docs/BRANCH_ARCHIVE.md)
and [original diagnostic notes](https://github.com/BananaOnGitHub/Streamside/blob/archive/build46-image-result/docs/EMOTE_DIAGNOSTIC.md).

## Build 47 request-decision investigation

Purpose: distinguish native static/animated request choice and cache lookup
observations from image-identity reuse. It preserves build 46 as its parent.

Added six exact native requester wrappers, donor-guarded NSCache lookup-site
classification, weak cache/result correlations and bounded GIF/WebP container
metadata. The recorded empty/nonempty cache result does not prove native type,
expiry or acceptance; `accepted=unknown` remains deliberate. No speculative
Swift enum decoding, cache replacement or playback mutation was introduced.

The archive preserves this investigation and its coverage limits. It does not
claim that the instrumentation itself resolved the frozen-animation symptom.
See the archived [branch closure](https://github.com/BananaOnGitHub/Streamside/blob/archive/build47-request-decision/docs/BRANCH_ARCHIVE.md)
and [request/cache notes](https://github.com/BananaOnGitHub/Streamside/blob/archive/build47-request-decision/docs/EMOTE_DIAGNOSTIC.md#build-47-request-and-cache-decisions).

## RN chat-boundary investigation — builds 51–54 and 65

Purpose: locate the active Twitch 31.5 React Native chat path after legacy
ingress/presentation hooks stayed idle, then identify representation, layout,
composer and emote-info boundaries before adding production adapters.

Device reports establish `SRWebSocket → RCTWebSocketModule → websocketMessage`
delivery toward JS and native `TwitchEmoteInputView` catalog handoff. The
observed Hermes source fingerprint ties donor analysis to the tested bundle.
Static tracing connects code-to-ID maps, IRC emote ranges, RN emote parts and
image URLs. Paragraph `NSTextAttachment` objects are reconstructed inline-child
placeholders, not stable decoded-emote objects; width must agree with Fabric
inline measurement and the mounted image subtree.

After compat implemented incoming rendering, widths, local echo and composer
previews, the diagnostic branch merged compat through build 64 while retaining
its passive probes. Build 65 traced provider taps through the RN sheet and its
query-backed content gate. Later compat build-66 evidence confirms the provider
sheet path executes but query-backed native card content does not; the provider
card replacement belongs at that boundary. Subsequent implementation lives on
compat, not in this probe-only branch's extra tooling.

The final branch retains builds 51–54, build-53 device findings, representation
and native-seam analysis, build-65 info traces, bounded/privacy-preserving probes
and host/donor validation records. Historical limitations remain explicit,
including the toolchain blocker on the standalone native-seam investigation
and the absence of a live per-emote mount/image identity join. See its
[branch closure and evidence links](https://github.com/BananaOnGitHub/Streamside/blob/archive/rn-chat-boundary/docs/BRANCH_ARCHIVE.md).

## RN image-demand (builds 73-87)

Purpose: separate excessive RN library demand, cache admission delay and queue
overflow while preserving native Twitch layout, decoders and transport policy.

| Builds | Completed work and evidence |
| --- | --- |
| 73–77 | Passive demand, lifecycle and geometry observations; bounded compiled-runtime startup calculations; identified runaway full-catalog stationary demand. |
| 78 | Corrected owned fractional-column lengths using adjacent offsets, preserving the original RN algorithm. Device startup/reopen range stabilized at 0..11, 60 live library JS instances; observed scrolling peak was 130 instances with a 26-column mask. Retained host and compiled-Hermes regression baseline. |
| 79–82 | Bounded cache-first delivery independent of transfer admission; real Apple Foundation HTTP-cache/revalidation fixture; conservative eligibility/annotation rejection diagnostics; header-accessor comparison; network-proven receipts for eligible Date-less cache entries. |
| 83 | Independent bounded overflow recovery with coalescing, cancellation, expiry and admission limits; retained eight active / six background slots and existing priority. |
| 84–86 | Investigated blank legacy native Recent on first opening. Build 84's settlement alone did not fix the device symptom; build 85 exposed premature section-zero gap placement before sections arrived. Build 86 defers that gap and is user-confirmed. |
| 87 | Restores the emoji button's inactive tint during section handoff and resolves the weak input owner through a bound palette container after keyboard reparenting. Footer insertion/repair no longer waits for the default-mode timer during drag. User-confirmed. |

Build-82 E→F added 197 direct cache hits and only 18 Foundation tasks. All 18
new tasks were local-cache transactions and all additional transfer queue waits
were at most 250 ms; network transactions and stored receipts did not increase.
That demonstrates effective warm reuse. It does not show that the earlier
313 waits in the 1–5 second bucket were harmless, nor establish a reason to
alter scheduler throughput. Closing/reopening the menu in F changes the
activity attribution but does not invalidate the cache reuse counters.

The performance architecture remains frozen. Overflow recovery is retained as
a separate correctness change. Revisit throughput only if actual device
behavior demonstrates a remaining bottleneck. Historical phase/procedure text
in the linked reports is preserved as evidence, not an outstanding request for
unchanged-build diagnostic passes.

Evidence: [phase 1](EMOTE_DEMAND_PHASE1.md),
[phase 1B](EMOTE_DEMAND_PHASE1B.md),
[calculation and build-78 baseline](EMOTE_DEMAND_PHASE1B_CALCULATION.md),
[cache/overflow transport](EMOTE_IMAGE_TRANSPORT.md),
[cache-first implementation evidence](../EMOTE_CACHE_PHASE2.md),
[bounded overflow contract](../EMOTE_OVERFLOW_RECOVERY.md),
[legacy picker corrections](LEGACY_RECENTS_DIAGNOSTIC.md).

## Validation and retained build number

Build 87 passed the 117-test host suite (one Apple-only test skipped locally),
the required donor/Hermes gate, arm64 framework/dylib artifact checks and IPA
verification. Both build and real macOS Foundation-cache CI jobs passed for
`7f48f67ea9ee3273f6c312587fafac6e077b10ec`. The user then confirmed the footer
fix works. These are the existing build's checks; documentation closure makes
no additional runtime or on-device claims.

Each archived branch's closure changes only README/documentation. Its original
source, probe code, tests, build metadata and full ancestry remain intact.
