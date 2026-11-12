# SwiftUI CI and conservative tooling audit

## Preservation and scope

The audit began on clean `feat/native-frontend` at
`1a1459a4626c71d570dd3c850c5215099fe651a7`. [The starting inventory](SWIFTUI_CI_START_STATE.json)
records the branch, worktree, relevant native history and tracked generated/evidence
files before changes. `a9ae3c2` committed that inventory before implementation.
The verified UIKit checkpoint and all prior development branches remain unchanged.
No published history is rewritten or force-pushed.

The first increment establishes donor-free hosted compilation. Cleanup follows
that successful build and keeps the existing frontend, native account/GraphQL
bridge, runtime guards and diagnostic infrastructure intact. No playback, chat,
emote frontend or independent authentication flow is added.

## Build architecture and first successful run

`48300584c601f882ff26bba5a5cf87a4f48258ea` introduced the
[Native SwiftUI workflow](../../.github/workflows/native-swiftui.yml).
[Run 43131916232](https://github.com/BananaOnGitHub/Streamside/actions/runs/43131916232)
passed both Apple and Linux ABI jobs. Actions used Xcode 26.6 build 17F113,
Apple Swift 6.3.3, iPhoneOS SDK 26.5 and runner image `20261102.0473.1`.
[The concise validation receipt](SWIFTUI_CI_VALIDATION.json) preserves source,
component and toolchain identities. Both modes compiled, linked and passed ad-hoc signature verification and pure
Swift presentation tests. Foundation HTTP tests and five synthetic comparison
tests passed. Six tests emulated the Apple-compiled Swift ABI caller fixture;
seven component admission tests and five native-core tests also passed.
The components were downloaded and their source/toolchain/file identities verified
on Ubuntu. Neither this run nor its artifacts had the proprietary donor.

The existing Linux/Zig workflow keeps building/verifying native legacy products
and DEBs. Its Foundation job moves into the SwiftUI workflow to share the Apple
runner. Build path filters, duplicate internal-PR guards and concurrency avoid
unnecessary repeats. The documentation workflow covers development documentation
changes independently. Routine builds require no local VM, SSH alias or signing
credential. [The maintained build guide](../development/NATIVE_SWIFTUI_CI.md)
defines download, verification, local packaging and optional fallback use.

## Tooling classification

| Class | Retained role and disposition |
| --- | --- |
| Required source and reproducible build infrastructure | `native/` SwiftUI/C/Objective-C interoperability and exact-donor metadata, `src/`, Zig/Apple stubs, packaging metadata/icons, `build.sh`, Make targets, CI definitions, Apple input allowlist/worker, component verifier and local assembly remain version-controlled. Generated RN payload/layout/patch headers and the investigation registry remain required C build inputs; their generators/guards and validation receipts remain. |
| Useful development utilities | Mach-O manipulation/verification, artifact receipts, RN graft/replay validators, pinned Hermes runtime builder, donor inspection/auth investigation, device-report comparison, documentation checks and real/synthetic test fixtures remain. These support recovery and existing functionality. |
| Machine-specific infrastructure | Compiler installations/caches, donor packages, SSH aliases/configuration/keys and personal SDK selection belong outside Git. Generic worker and opt-in SSH transport code remain maintainable build support; no personal host is hardcoded into the normal path. Tests use `ZIG` or PATH, and ABI tests can use a precompiled Apple object. |
| Generated outputs | Frameworks, objects, Swift compiler products, IPAs, DEBs, build logs, SDK/derived data and signing material stay outside the checkout and are ignored as defense in depth. Artifact roots default outside the repository; CI uses runner temporary directories and explicit output allowlists. |
| Historical evidence | Device reports/archives, concise investigations, exact identities and meaningful failure/validation summaries remain active. Bulk copied logs/generated headers/manifests and one obsolete binary staging tool move out of the current tree with a published recovery tag and per-file hash inventory. |

## What was retired and preserved

The annotated tag `archive/workspace-build-records-2026-11` was published and
verified before removing anything. It targets the exact starting revision above.
[The recovery index](../archive/WORKSPACE_BUILD_RECORDS.md) and
[172-file inventory](../archive/WORKSPACE_BUILD_RECORDS.json) retain retrieval
instructions and SHA-256 identities for 2,097,341 bytes removed from the active
tree: 161 copied record files, raw cleanup logs, the old local workspace note,
and `tools/stage_r5_production.py`. That R5 tool reproduces an old binary candidate;
it is superseded by source-backed packaging and is not imported by active tests
or tools. Its distinct historical behavior remains recoverable.

No donor, test IPA, signing material or compiler installation was newly committed.
No existing device evidence, native guards, Zig infrastructure, diagnostic schema,
source-required generated header or unique investigation finding was discarded.
The working checkout becomes smaller; historical Git objects intentionally remain.
Historical paths inside old receipts remain evidence, not environment defaults.
The current Hermes receipt is regenerated by its required runtime test after
portable compiler selection changes; its predecessor is preserved separately.

## Validation limits and next frontend work

The first hosted build establishes Apple compilation and automated validation.
The local packaging integration consumes verified components, retaining exact
compiled and assembly revisions separately. Final integration results are appended
after the updated workflow and local exact-donor assembly are checked.

The account/listing implementation remains the proven native service adapter.
The SwiftUI shell and native logout still need physical-device validation for
these new component/package identities. Fresh login remains blocked on the
validated hosted-portal completion/challenge contract and ingress into the native
first-party session authority, as recorded in [authentication findings](SWIFTUI_NATIVE_FOUNDATION_TWITCH_32.md).
A working compiler does not establish that contract. No guessed Swift witness,
credential extraction or hidden RN fallback is introduced.
