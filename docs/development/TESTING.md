# Testing

Tests are organized around production boundaries. Record what ran, what failed, and what skipped; do not turn an unavailable donor/device into a passing result.

## Main gates

| Gate | Command | Requirement and evidence |
| --- | --- | --- |
| Native artifact contract | `make verify` | Build both arm64 identities and check fingerprints/layout/signatures |
| Host suite | `make test` | Production helpers/adapters, Python tooling, JS fixtures; platform/private-input checks can skip |
| DEB packaging | `make deb` | Rootful/rootless data archives match verified build bytes |
| Apple HTTP cache | `make test-foundation-cache` | macOS/Xcode required; cannot skip |
| Compiled RN virtualization | `make test-rn-virtualization` | Five explicit donor/runtime/compiler variables; cannot skip |
| Final IPA | `tools/verify_ipa.py` | Finished unsigned IPA matches the expected framework and app contract |
| Device acceptance | Focused manual matrix | Actual rendering, interaction, keyboard, playback, and lifecycle on the target configuration |

CI's Linux job runs `make verify test deb`; macOS runs the Foundation gate. The workflow uploads artifacts and verifies version tags but does not publish releases. Private-donor Hermes validation and iOS device checks are separate.

## Feature-to-test map

| Area | Relevant tests |
| --- | --- |
| Playback/protocol lifecycle | `test_protocol.py` |
| Privacy/log labels | `test_privacy.py` |
| Provider limits/fetch lifetime | `test_emote_fetch.py`, `test_emote_fetch_lifetime.py` |
| Identity/images/geometry | `test_emote_images.py`, `test_emote_geometry.py`, `test_emote_ui.py` |
| RN incoming/own-message/width | `test_rn_incoming.py`, `test_rn_width.py` |
| Legacy presentation | `test_emote_presentation.py` |
| Composer/preview/details | `test_composer.py`, `test_composer_preview.py`, `test_composer_details.py`, `test_rn_composer_ui.py` |
| Picker/native catalogs/recents | `test_native_picker.py`, `test_emote_picker.py`, `test_recent_snapshot.py`, `test_catalog_compatibility.py` |
| Library/backspace/settings | `test_composer_library.py`, `test_rn_library.py`, `test_rn_backspace.py`, `test_rn_strip.py` |
| Provider cards | `test_rn_popup.py`, `test_provider_presentation_route.py` |
| HTTP cache/receipts/overflow | `test_cache_protocol.py`, `test_http_cache.py`, `test_cache_annotation.py`, `test_cache_receipt.py`, `test_image_overflow.py` |
| Foundation integration | `test_foundation_cache.py`, native Foundation fixtures |
| Demand/runtime probes | `test_image_demand.py`, `test_rn_calculation_boundary.py`, `test_rn_snapshot_runtime.py`, `test_legacy_palette_probe.py` |
| Artifact tooling | `test_tools.py`, `test_artifact_guard.py` |

Files are under [tests](../../tests). Sanitizer-backed native harnesses compile actual production sections/helpers with controlled ABI adapters. Read a test's setup before claiming it exercises a real iOS class.

## Compiled Hermes baseline

The required gate uses the original admitted donor, Hermes-98 runtime source `40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c`, the matching compiler, and a fingerprinted runner.

It executes the production graft and native snapshot parser rather than a source-only mock. It exercises:

- Native snapshot acceptance and bounded preparation/refusal stages.
- The actual donor overlap/window functions with production `getItemLayout`.
- Twelve viewport widths, six catalog sizes, and two feature-flag branches: 7,344 window calculations across first opening, repeated idle calculations, eleven scroll positions, and a fresh reopening.
- Contiguous fractional endpoints, bounded ranges, visible-column inclusion, five-row mapping, and stable logical identities.
- Real donor settings registration: Metro module 4880 versus factory function 4884.
- Unchanged settings factory/component behavior with optional containerSections props and subpages.

The record includes input/source/payload/compiler/runner hashes. A diagnostic build checks it before compiling. A record becomes stale when its fingerprinted inputs change.

See [Building](../BUILDING.md) for commands and [the calculation archive](../archive/investigations/EMOTE_DEMAND_PHASE1B_CALCULATION.md) for the failed probes and maintained baseline.

## Real Foundation checks

The macOS fixture uses a local HTTP server and real NSURLSession/NSURLCache behavior. It distinguishes network/cache transactions, conditional validation, policy/variant restrictions, Date-bearing freshness, and network-proven Date-less receipts.

Early candidates failed because completion-handler tasks bypassed cache-proposal callbacks, delegate/session lifecycle was incomplete, or the test did not pump the run loop. The current gate executes delegate data tasks and settled receipt/annotation accounting. These corrections are preserved in [Cache investigation](../archive/investigations/EMOTE_CACHE_PHASE2.md).

Linux can verify controlled cache helpers but cannot establish Apple's cache callback behavior. Its explicit Apple-only skip remains a skip.

## Device matrix

Record app/build, iOS/device, installation/signing route, Streamside bundle, renderer, and whether the catalog/cache was cold or warm.

Compatibility claims should cover only established device/iOS/signing configurations. Framework minimum-version metadata does not lower the Twitch app's minimum iOS version. Build and fixture results do not replace device acceptance; see [Compatibility](../COMPATIBILITY.md) for the current jailbreak validation limits.

For chat: incoming and ordinary sent text/native/provider mixes, square/wide/animated providers, emoji before a code, repeated names, replies, channel switches, scrolling, and unknown/native identities. Treat `/me` separately.

For the composer: editing/selection/undo/clipboard, whole-emote deletion, first-download previews, long GIF holds, foreground/background, inline prediction acceptance/cancellation, and an IME case.

For the library: first open, stationary large catalog, gradual/rapid/backward scrolling, close/reopen, provider/scope changes, stable Recent order, labels/accessibility, footer navigation, holds, and keyboard reparenting on legacy.

For playback: an actual ad-bearing preroll/midroll case, main/PiP/profile preview overlap, ownership misses, alternate failures, and recovery. Clean counters without an ad-bearing case are insufficient.

## Evidence discipline

Keep source admission, fixture execution, device counters, and visible outcomes separate. Record unsuccessful attempts and superseding commits. A reconstructed source and a byte-identical independently reproduced artifact are different provenance claims.

Tests do not justify unsupported performance claims. Queue wait, task completion, onLoad, and displayed pixels are different boundaries.

[Contributing](../../CONTRIBUTING.md) · [Architecture](../ARCHITECTURE.md) · [Diagnostics](../features/DIAGNOSTICS.md)
