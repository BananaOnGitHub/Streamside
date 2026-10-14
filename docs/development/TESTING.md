# Testing

Tests are organized around production boundaries. Record what ran, what failed, and what skipped; do not turn an unavailable donor/device into a passing result.

## Main gates

| Gate | Command | Requirement and evidence |
| --- | --- | --- |
| Documentation integrity | `make docs-check` | Offline Markdown links/anchors/assets and current version metadata; includes the archive |
| Native artifact contract | `make verify` | Build both arm64 identities and check fingerprints/layout/signatures |
| Host suite | `make test` | Production helpers/adapters, Python tooling, JS fixtures; platform/private-input checks can skip |
| DEB packaging | `make deb` | Rootful/rootless data archives match verified build bytes |
| Apple HTTP cache | `make test-foundation-cache` | macOS/Xcode required; cannot skip |
| Compiled RN virtualization | `make test-rn-virtualization` | Five explicit donor/runtime/compiler variables; cannot skip |
| RN transcript trace | `make test-chat-trace` | Diagnostic-only chat graft, compiled observer/native handler; same five inputs, cannot skip |
| Final IPA | `tools/verify_ipa.py` | Finished unsigned IPA matches the expected framework and app contract |
| Device acceptance | Focused manual matrix | Actual rendering, interaction, keyboard, playback, and lifecycle on the target configuration |

CI's Linux job runs `make verify test deb`; macOS runs the Foundation gate. The workflow uploads artifacts and verifies version tags but does not publish releases. Private-donor Hermes validation and iOS device checks are separate.

## Documentation integrity

The separate **Documentation** workflow runs on pull requests, pushes to `main`, and manual dispatch. Its **Documentation check** job uses Ubuntu and Python 3.12's standard library, with `contents: read`. It runs the validator's focused tests and then the complete documentation corpus. Failures identify the originating file, line, and reason through Actions annotations.

Run it locally from a Git checkout:

```sh
make docs-check
python3 -m unittest discover -s tests -p test_docs.py -v
```

[check_docs.py](../../tools/check_docs.py) checks every tracked Markdown file, plus untracked Markdown files not excluded by Git ignore rules. Generated, ignored build output is outside the corpus; there is no archive exemption or link allowlist. Tracked files remain checked even if an ignore rule matches them.

The check validates:

- Inline links/images, full/collapsed/shortcut reference links, and HTML `href`/`src` references, including linked images.
- Relative and repository-root paths to documents, images, assets, source files, tests, scripts, and directories. Percent-encoded paths are decoded once; query strings do not change the target. Missing targets, checkout escapes, invalid escapes, and malformed explicit link destinations fail.
- Same-document and cross-document Markdown fragments, with percent decoding, ATX/Setext headings, visible heading text, GitHub-style punctuation/case/spacing rules, and duplicate-heading suffixes. Explicit HTML `id`/`a name` anchors and GitHub's `user-content-` prefix are also recognized.
- `VERSION` as `X.Y.Z`, the framework plist's `CFBundleShortVersionString` as that public identity, `CFBundleVersion` as `X.Y.Z.build`, and `TAS_REPORT_VERSION` as `X.Y.Z-build.build` with the same positive internal build number.

Absolute URI schemes (including HTTP(S), `mailto`, `tel`, and `data`) and protocol-relative URLs are excluded from target checking; the validator makes no network requests. Source/asset fragments are renderer-specific and only their file existence is checked. Fenced/indented code, inline code, HTML comments, footnotes, arbitrary identifiers, and historical filenames in prose are not repository references. An undefined standalone `[label]` is Markdown text, while an explicit undefined `[label][reference]` is reported.

Historical source that no longer exists can be linked through an immutable commit URL, with its revision and scope stated in the record. That is an external historical reference, not an exemption from checking other links in the same file. No obsolete source tree is required solely to preserve an investigation.

Version checks are limited to those three current metadata locations. They do not scan version numbers in prose, changelog/history/archive records, Twitch donors, unrelated plists, or generated artifacts. DEB metadata derives from `VERSION`; artifact verification remains in the build/package gates. The existing Build workflow retains responsibility for release-tag validation.

Heading slugs are a maintained approximation of GitHub's rendered anchors, not a claim of complete rendering parity. Unusual inline constructs and new heading forms need fixtures checked against their rendered GitHub anchors before relying on them.

The reader supports the Markdown forms used in this repository; it is not a full CommonMark renderer. Multiline reference definitions, complex HTML layout, and headings nested inside lists need additional fixture coverage before being adopted. External URLs and non-Markdown fragments still need human review.

This gate validates structure and declared current metadata. It does not require unfinished features to appear in public guides, assess implementation accuracy or readiness, prove compatibility or device testing, or judge changelog completeness. Those remain the feature-freeze review responsibilities in [Documentation maintenance](DOCUMENTATION.md).

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
| RN transcript trace | `test_chat_trace.py`, compiled `make test-chat-trace` fixtures |
| Documentation validator | `test_docs.py` |
| Artifact tooling | `test_tools.py`, `test_artifact_guard.py` |

Files are under [tests](../../tests). Sanitizer-backed native harnesses compile actual production sections/helpers with controlled ABI adapters. Read a test's setup before claiming it exercises a real iOS class.

## Compiled Hermes baseline

The required gate uses the original admitted donor, Hermes-98 runtime source `40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c`, the matching compiler, and a fingerprinted runner.

It executes the production graft and native snapshot parser rather than a source-only mock. It exercises:

- Native snapshot acceptance and bounded preparation/refusal stages.
- The actual donor overlap/window functions with production `getItemLayout`.
- Twelve viewport widths, six catalog sizes, and two feature-flag branches: 7,344 window calculations across first opening, repeated idle calculations, eleven scroll positions, and a fresh reopening.
- Contiguous fractional endpoints, bounded ranges, visible-column inclusion, five-row mapping, and stable logical identities.
- Current Twitch 31.6 donor settings registration: Metro module 4937 versus factory function 4941. The archived 31.5 evidence retains its original 4880/4884 binding.
- Unchanged settings factory/component behavior with optional containerSections props and subpages.

The record includes input/source/payload/compiler/runner hashes. A diagnostic build checks it before compiling. A record becomes stale when its fingerprinted inputs change.

See [Building](../BUILDING.md) for commands and [the calculation archive](../archive/investigations/EMOTE_DEMAND_PHASE1B_CALCULATION.md) for the failed probes and maintained baseline.

## RN transcript trace build

`CHAT_TRACE_DIAGNOSTIC=1` is a separate, opt-in diagnostic build, not the emote-library demand probe or a row-layout fix. Run `make test-chat-trace` with `TAS_RN_DONOR`, `ZIG`, `TAS_HERMESC`, `TAS_HERMES_SNAPSHOT_RUNNER`, and `TAS_HERMES_SOURCE` set as for the compiled Hermes baseline, then:

```sh
CHAT_TRACE_DIAGNOSTIC=1 make verify
```

[validate_chat_trace.py](../../tools/validate_chat_trace.py) writes `build/chat-trace-validation.json`; the build rejects missing, failed, or stale records. `CHAT_TRACE_VALIDATION` can select another record. The gate regenerates owned bytecode, applies the production six-stage C chain, checks unchanged predecessor functions/constants/debug data, and executes both the installer and donor factory/export join in pinned Hermes through the production native handler. Controlled React/store/measurement and Objective-C boxing adapters are not Fabric, RCTMethod, or device validation.

Normal builds omit the sixth graft and trace bridge. The current trace runs continuously with bounded event rings, rotating correlation caches and separate flow/geometry/priority rate limits. The native report provides elapsed time, retention bounds, lifecycle cycles, sample frames and coverage losses. Compiled tests use controlled JS/native clocks to exercise late reopening and long logical runs; they do not claim an equivalent duration of real device testing.

The trace is content-free and read-only with respect to chat state; it has diagnostic overhead and can miss throttled, unmeasured, filtered or overwritten evidence. Copy the report when the symptom appears, before restarting the process. Current capture instructions and limits live in the [rolling-trace investigation](../investigations/RN_CHAT_ROW_GAPS.md#build-8-rolling-trace-trial); the earlier build-7 trial is preserved there.

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
