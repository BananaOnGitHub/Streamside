# Research archive

These records preserve the investigation sequence, attempted approaches, failures, corrections, and validation evidence. They are not current installation instructions or a list of unfinished features.

Each record identifies its original source revision and links to its current successor. Historical procedures/status paragraphs retain the scope of their build; later confirmation does not erase what an earlier attempt failed to establish.

[History](../HISTORY.md) is the chronological entry point. [Architecture](../ARCHITECTURE.md) and [feature guides](../features/third-party-emotes/README.md) describe the current implementation.

## Investigations

| Record | What it established and retained limits | Current guide |
| --- | --- | --- |
| [NATIVE_EMOTES](investigations/NATIVE_EMOTES.md) | Native Swift catalog publication/bridging, input authority, stable image identity, selector failures, geometry/animation ownership; old unslid addresses are donor-specific | [Picker](../features/third-party-emotes/EMOTE_PICKER.md), [Composer](../features/third-party-emotes/COMPOSER.md) |
| [EMOTE_DIAGNOSTIC](investigations/EMOTE_DIAGNOSTIC.md) | Builds 39–45 target-code, transport, playback/decode/native-handoff observations; weak identity reuse is not a proven cache hit | [Diagnostics](../features/DIAGNOSTICS.md) |
| [EMOTE_DEMAND_PHASE1](investigations/EMOTE_DEMAND_PHASE1.md) | Build-73 demand/lifecycle units, privacy budgets, and reconstructed-source versus byte-identical-framework provenance | [Image transport](../features/third-party-emotes/IMAGE_TRANSPORT.md) |
| [EMOTE_DEMAND_PHASE1B](investigations/EMOTE_DEMAND_PHASE1B.md) | Build-74 viewport/mask/mount/asset/flight distribution and full-catalog stationary demand; native view identity remains unestablished | [Picker](../features/third-party-emotes/EMOTE_PICKER.md) |
| [EMOTE_DEMAND_PHASE1B_CALCULATION](investigations/EMOTE_DEMAND_PHASE1B_CALCULATION.md) | Failed captures, literal-kind correction, throwing helper, exact fractional gap, real RN reproduction, build-78 device baseline and compiled gate | [Picker](../features/third-party-emotes/EMOTE_PICKER.md), [Testing](../development/TESTING.md) |
| [EMOTE_CACHE_PHASE2](investigations/EMOTE_CACHE_PHASE2.md) | Builds 79–82 cache-first lane, failed Apple candidates, first-rejection accounting, actual Date absence, proven original receipts; warm reuse evidence is scoped | [Image transport](../features/third-party-emotes/IMAGE_TRANSPORT.md) |
| [LEGACY_RECENTS_DIAGNOSTIC](investigations/LEGACY_RECENTS_DIAGNOSTIC.md) | Build-84 failed settlement, build-85 section-zero gap evidence, build-86 publication guard, build-87 reparented footer/tint corrections | [Picker](../features/third-party-emotes/EMOTE_PICKER.md) |
| [TWITCH_31_5_SENT_EMOTES](investigations/TWITCH_31_5_SENT_EMOTES.md) | Removed old local-delivery prerequisites/selectors and why incoming/composer success did not establish own-message rendering | [Chat rendering](../features/third-party-emotes/CHAT_RENDERING.md) |
| [TWITCH_31_5_PRESENTATION_BOUNDARY](investigations/TWITCH_31_5_PRESENTATION_BOUNDARY.md) | Legacy call-chain/definition construction, rejection of late-display seams, account/channel ownership and static-analysis limits | [Chat rendering](../features/third-party-emotes/CHAT_RENDERING.md) |
| [ARCHITECTURE_BASELINE](investigations/ARCHITECTURE_BASELINE.md) | Prior main architecture, including superseded preview/picker/pending claims; preserved to audit extracted implementation knowledge | [Architecture](../ARCHITECTURE.md) |

## RN boundary research

These five records originally existed only on the RN diagnostic branch. They are now indexed historical copies, not additional production adapters.

| Record | Finding or limitation |
| --- | --- |
| [RN_CHAT_BOUNDARY_PROBE](investigations/RN_CHAT_BOUNDARY_PROBE.md) | Observed IRC receive, bridgeless surfaces, native input, and source fingerprint |
| [RN_BUILD53_FINDINGS](investigations/RN_BUILD53_FINDINGS.md) | Cumulative A–C observations, catalog shape/identities, attachment observations, and evidence gaps |
| [RN_EMOTE_REPRESENTATION](investigations/RN_EMOTE_REPRESENTATION.md) | Code-to-ID/range/parser/URL reconstruction and candidate integration boundaries |
| [RN_NATIVE_PRESENTATION_SEAM](investigations/RN_NATIVE_PRESENTATION_SEAM.md) | Reconstructed paragraph placeholders, Fabric measurement, missing live per-emote identity join, and standalone toolchain blocker |
| [RN_EMOTE_INFO_TRACE](investigations/RN_EMOTE_INFO_TRACE.md) | Build-65 tap/sheet/query-backed-content gate; provider-card implementation followed at that boundary |

## Implementation experiments

| Record | Attempt and outcome |
| --- | --- |
| [TWITCH_31_5_COMPATIBILITY](experiments/TWITCH_31_5_COMPATIBILITY.md) | Build-48 donor/package record and subsequent compatibility status; original donor hashes/guards preserved |
| [TWITCH_31_5_PRESENTATION_TRIAL](experiments/TWITCH_31_5_PRESENTATION_TRIAL.md) | Build-50 legacy native definitions and asset-type/authority checks; not proof of RN rendering |
| [RN_INCOMING_SYNTHETIC_TRIAL](experiments/RN_INCOMING_SYNTHETIC_TRIAL.md) | Build-55 incoming-only scope, original frame/body preservation, native/shared-room gates, observed images |
| [RN_INCOMING_WIDTH_TRIAL](experiments/RN_INCOMING_WIDTH_TRIAL.md) | Build-56 exact-body width aliases and coordinated wrapper/image geometry before Fabric |
| [RN_LOCAL_ECHO_TRIAL](experiments/RN_LOCAL_ECHO_TRIAL.md) | Failed 57/58 seam, disappearing build-59 messages, Call4 clobber, frame-21/catch correction, host/donor/device evidence |
| [RN_COMPOSER_PREVIEW_TRIAL](experiments/RN_COMPOSER_PREVIEW_TRIAL.md) | Placeholder-only 61, URL overload 62, proportions/GIF 63, cold-start 64, provisional-input guard 89 |
| [RN_PROVIDER_INFO_TRIAL](experiments/RN_PROVIDER_INFO_TRIAL.md) | Build-66 owned card within native sheet, native-card fallback, metadata/actions and graft checks |
| [RN_HORIZONTAL_PICKER_TRIAL](experiments/RN_HORIZONTAL_PICKER_TRIAL.md) | 67/68 scoped suggestion/input hooks, native catalog authority, writable exports and autocomplete takeover |
| [RN_LIBRARY_PORT](experiments/RN_LIBRARY_PORT.md) | 69/70 tray sections, five-row geometry, recents, footer refs and whole-token backspace |
| [EMOTE_IMAGE_TRANSPORT](experiments/EMOTE_IMAGE_TRANSPORT.md) | 71 shared transport and 72 cancellation-safe detached flights/reserved admission; later cache/overflow summary |
| [EMOTE_OVERFLOW_RECOVERY](experiments/EMOTE_OVERFLOW_RECOVERY.md) | Build-83 bounded recovery, original deadlines/coalescing/cancellation, no independent downloader or throughput bump |

## Release and baseline records

| Record | Why it is retained |
| --- | --- |
| [R5_PRODUCTION_STAGE](releases/R5_PRODUCTION_STAGE.md) | Exact-input binary staging while original source was unavailable; R6 failure/R7 correction and hashes |
| [RELEASE_2.2.1](releases/RELEASE_2.2.1.md) | Historical candidate identity, separate from current published replacement |
| [RELEASE_2.2.1-jb](releases/RELEASE_2.2.1-jb.md) | Package names/hashes, source-parity evidence, explicit untested-jailbreak status |
| [DEVELOPMENT_CHANGELOG](releases/DEVELOPMENT_CHANGELOG.md) | Original mixed release/development diary; unique intermediate build notes preserved outside public changelog |
| [HISTORY_BASELINE](releases/HISTORY_BASELINE.md) | Original reconstruction confidence, binary evidence and consolidation/refinement records |
| [RELEASE_PREPARATION_BASELINE](releases/RELEASE_PREPARATION_BASELINE.md) | Prior main README's engineering status/device chronology, preserved while the current README becomes user-focused |

The current published 2.2.1 IPA digest is `c930d39a28c9abf4a6d4e5fb8f042b84c58f648c5c31a3ee3ff5172e3d3e1d6a`. The candidate note's different hash is not overwritten. GitHub releases can replace assets without changing a historical checked-in note; both identities belong in the history.

## Archived branches

| Branch | Last implementation/probe head | Closure head and local record | Integration disposition |
| --- | --- | --- | --- |
| [archive/diagnostic/build46-image-result](https://github.com/BananaOnGitHub/Streamside/tree/archive/diagnostic/build46-image-result) | `b074e6f0c6e17771a64783deb70eb8baebe38c27` | [Closure](branches/build46-image-result/BRANCH_ARCHIVE.md) | Independent result-construction/reuse probes; not merged wholesale |
| [archive/diagnostic/build47-request-decision](https://github.com/BananaOnGitHub/Streamside/tree/archive/diagnostic/build47-request-decision) | `1f58c73fd36a28e72e71994e184eb495d8a05c67` | [Closure](branches/build47-request-decision/BRANCH_ARCHIVE.md) | Independent native requester/cache decisions; unresolved acceptance remains unknown |
| [archive/diagnostic/rn-chat-boundary](https://github.com/BananaOnGitHub/Streamside/tree/archive/diagnostic/rn-chat-boundary) | `82c3251ffc895ecb3d4f769b61ac13d322895afc` | [Closure](branches/rn-chat-boundary/BRANCH_ARCHIVE.md) | Passive representation/presentation/info research; independent probes remain historical |
| [archive/diagnostic/rn-image-demand](https://github.com/BananaOnGitHub/Streamside/tree/archive/diagnostic/rn-image-demand) | `7f48f67ea9ee3273f6c312587fafac6e077b10ec` | [Closure](branches/rn-image-demand/BRANCH_ARCHIVE.md) | Completed demand/cache/overflow/legacy corrections incorporated into compatibility/main |

The individual closure records preserve their immutable closure revision in the context banner. They are not flattened into one BRANCH_ARCHIVE file.

Additional branch-specific [build-46 diagnostic](branches/build46-image-result/EMOTE_DIAGNOSTIC.md) and [build-47 diagnostic](branches/build47-request-decision/EMOTE_DIAGNOSTIC.md) records preserve findings not present in main's build-45 report.

[CLOSURE_BUILD87](branches/CLOSURE_BUILD87.md) retains the former main archive index and integration/validation account. [archive/compat/twitch-31.5](https://github.com/BananaOnGitHub/Streamside/tree/archive/compat/twitch-31.5) retains the final build-92 compatibility head; [archive/twitch-31.5-build50-legacy-chat](https://github.com/BananaOnGitHub/Streamside/tree/archive/twitch-31.5-build50-legacy-chat) retains the legacy baseline. Earlier release/emote archive branches remain available for provenance.

## Reading old status and procedures

“Pending,” “next test,” or an obsolete donor address belongs to the historical experiment's scope. Use the linked current guide and later History entry for the retained implementation.

Original source, reconstructed source, independently reproduced binary, automated validation, and visible device confirmation remain separate kinds of evidence. An absent report/build mapping is not filled by inference.

The current documentation does not request unchanged-build diagnostic passes or imply the completed integrations are still trials. Preserve a record's distinctive findings while following its superseding correction.
