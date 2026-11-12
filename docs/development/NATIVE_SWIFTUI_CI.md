# SwiftUI builds with GitHub Actions

Ubuntu owns source editing, donor inspection, Linux tests, orchestration and IPA
assembly. The [Native SwiftUI workflow](../../.github/workflows/native-swiftui.yml)
uses a standard GitHub-hosted `macos-26` runner for Apple compilation. It selects
`/Applications/Xcode_26.6.app` and validates Xcode 26.6 build 17F113 and iPhoneOS
SDK 26.5 against [the toolchain pin](../../native/apple-toolchain.json). Missing or
changed tools fail the build. Compiler, Swift version and runner image identities
are recorded with the outputs. Do not rely on the runner's default Xcode selection.

The routine workflow uses no SSH host, donor IPA, signing certificate or account
credential. Its isolated compiler workspace contains an explicit allowlist of
owned C, Objective-C and Swift sources, tests and generated admission metadata.
The donor-specific plan is already source-controlled metadata; donor images,
JavaScript bundles and donor frameworks are not uploaded.

## Workflow outputs and validation

Both baseline and native arm64 iOS 16.4 frameworks are compiled and linked with
SwiftUI, UIKit, Foundation and Combine. The worker verifies ad-hoc signatures and
runs the pure Swift model tests. The Apple job also runs the real Foundation HTTP
fixture and synthetic report comparisons. A Linux job downloads the components,
checks every hash/source identity and runs six calling-convention tests against
the Apple-compiled ABI fixture, component admission tests and native core tests.
No Twitch account, network service or iOS application executes in these tests.

The downloadable `swiftui-components-<source-sha>` artifact contains only owned
frameworks, the generated Objective-C interface/admission header, the ABI caller
object, compiler logs and `components.json`. The manifest identifies source
revision, proof, admission plan, every file hash and successful Apple validation.
The compiler receipt includes the workflow run identity. Require a successful
whole workflow run, including its Linux ABI job, before device packaging.
Artifacts are retained for 14 days; commit meaningful findings and identities to
development records rather than copying all raw outputs into the source tree.
Failed builds retain only explicit error/log paths for seven days and remain failed.

Path filters avoid compiling for documentation-only changes. Internal pull
requests use their branch push run; fork pull requests get a read-only run.
Concurrency cancels superseded runs. The existing Linux/Zig workflow remains
independent; the Foundation check now shares the SwiftUI macOS job.

## Download and assemble on Ubuntu

In GitHub, open **Actions → Native SwiftUI**, choose a successful push run for the
development branch, and download its components artifact. Alternatively, from
the checkout with an authenticated GitHub CLI:

```sh
# Choose the successful run shown in Actions, then use its numeric ID here.
NATIVE_RUN_ID=43132946716
NATIVE_SOURCE_SHA="$(gh run view "$NATIVE_RUN_ID" --json headSha --jq .headSha)"
gh run download "$NATIVE_RUN_ID" --name "swiftui-components-$NATIVE_SOURCE_SHA" --dir "../artifacts/ci/$NATIVE_RUN_ID"
python3 tools/native_frontend/components.py verify --output "../artifacts/ci/$NATIVE_RUN_ID"
python3 tools/native_frontend/build.py --frontend swiftui --components "../artifacts/ci/$NATIVE_RUN_ID" --donor ../donors/tv.twitch-32.0.ipa --mode both
```

The example run establishes the pipeline; select a run matching the current
native source/proof for packaging. Component verification rejects corrupted files,
unexpected files/symlinks, changed toolchains, missing validation, changed native
source/proof and regenerated admission-header mismatches. A later documentation-only
commit may consume a component built from an ancestor with the same source/proof;
the compiled revision remains the component revision, and the local assembly
revision is recorded separately. No stale component is silently recompiled via SSH.

Local packaging verifies the exact inspected Twitch 32.0 donor and native ABI
boundaries before mutation. It preserves all unrelated donor entries and original
HBC, adds probes/guarding and assembles the paired IPAs under external artifacts.
Choose a new output directory for each assembly; nonempty destinations are rejected.
No donor or final IPA is sent to Actions.

Sign the resulting IPA locally with Feather and install it on the physical
iPhone. Preserve the appropriate app/keychain identity when testing restoration.
Follow [the native device checklist](../investigations/SWIFTUI_NATIVE_DEVICE_TEST.md).
Compilation and packaging do not establish session restoration, native logout,
real follows, baseline positive control, zero runtimes or startup/memory changes.
The existing fresh-login blocker is unchanged; see [authentication findings](../investigations/SWIFTUI_NATIVE_FOUNDATION_TWITCH_32.md).

## Optional local Mac fallback

For interactive debugging, an independently configured Mac may run
`python3 tools/native_frontend/components.py build --output /external/output`
with the pinned Xcode selected through `DEVELOPER_DIR`. The existing generic SSH
adapter remains available only when explicitly requested with `--apple-build-host`.
Per-machine SSH aliases and key files live outside the repository. No previous VM
or alias is required or assumed available. The UIKit/Zig recovery path is unchanged.

This pins/validates the Apple toolchain and inputs; it does not promise identical
Mach-O UUIDs or bytes across arbitrary runner images. Every delivered output has
its own exact hash. See [workspace guidance](WORKSPACE.md) and [the tooling audit](../investigations/SWIFTUI_CI_AND_TOOLING_AUDIT.md).
