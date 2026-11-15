# Hosted SwiftUI compilation and local assembly

Ubuntu owns source editing, donor inspection, Linux tests, orchestration and IPA
assembly. [Hosted Apple build instructions](APPLE_BUILDS.md) define the normal
Codemagic-preferred selection and GitHub Actions fallback. Both providers use
[the shared Apple runner](../../tools/apple_ci.py) and validate Xcode 26.6 build
17F113 and iPhoneOS SDK 26.5 against [the toolchain pin](../../native/apple-toolchain.json).
GitHub explicitly selects `/Applications/Xcode_26.6.app`; Codemagic selects the
26.6 image. Missing or changed tools fail the build. Compiler and Swift version
identities are recorded with the outputs.

The routine workflow uses no SSH host, donor IPA, signing certificate or account
credential. Its isolated compiler workspace contains an explicit allowlist of
owned C, Objective-C and Swift sources, tests and generated admission metadata.
The donor-specific plan is already source-controlled metadata; donor images,
JavaScript bundles and donor frameworks are not uploaded.

## Workflow outputs and validation

Both baseline and native arm64 iOS 16.4 frameworks are compiled and linked with
SwiftUI, UIKit, Foundation and Combine. The worker verifies ad-hoc signatures and
runs the pure Swift model tests. The Apple job also runs the real Foundation HTTP
fixture and synthetic report comparisons. Ubuntu retrieval checks every hash/source identity and runs 17 calling-convention
tests against the Apple-compiled ABI fixture, component admission and native core
tests. The GitHub fallback additionally runs those gates in its Linux job.
No Twitch account, network service or iOS application executes in these tests.

The component archive contains only owned frameworks, the generated Objective-C
interface/admission header, the ABI caller object, compiler logs and
`components.json`. Its manifest identifies source revision, proof, admission
plan, every file hash and successful Apple validation. The enclosing
`validation.json` identifies the archive hash and shared Apple gate outcomes.
Provider run IDs and download verification are recorded in the external local
build ticket. Require successful Apple compilation and Ubuntu verification
before device packaging. Keep meaningful findings and identities in development
records rather than copying raw outputs into the source tree.

Apple compilation is requested explicitly to avoid duplicate provider jobs.
The existing Linux/Zig workflow remains independent and automatic. Both providers
run the Foundation check in the Apple job. Neither uses the local VM routinely.

## Download and assemble on Ubuntu

After committing and pushing, run `make native-ci`. Use `make native-ci-status`
to inspect that exact build and `make native-ci-fetch` after success. See
[the operational guide](APPLE_BUILDS.md) for authentication, budget checks,
resumable tickets and failure handling.

Pass the verified components path printed by retrieval to local packaging:

```sh
python3 tools/native_frontend/build.py --frontend swiftui --components /external/path/printed/by/fetch --donor ../donors/tv.twitch-32.0.ipa
```

Component verification rejects corrupted or unexpected files, symlinks, changed
toolchains, missing validation, changed native source/proof and regenerated
admission-header mismatches. A later documentation-only commit may consume a
component built from an ancestor with the same source/proof; the compiled
revision remains the component revision, and the local assembly revision is
recorded separately. No stale component is silently recompiled via SSH.

Local packaging verifies the exact inspected Twitch 32.0 donor and native ABI
boundaries before mutation. It preserves all unrelated donor entries and original
HBC, adds probes/guarding and assembles the diagnostic IPA under external artifacts. An independent original-startup
control remains an explicit optional packaging mode.
Choose a new output directory for each assembly; nonempty destinations are rejected.
No donor or final IPA is sent to Actions.

Sign the resulting IPA locally with Feather and install it on the physical
iPhone. Preserve the appropriate app/keychain identity when testing restoration.
Follow [the native device checklist](../investigations/SWIFTUI_NATIVE_DEVICE_TEST.md).
Compilation and packaging do not establish session restoration, native logout,
real follows, baseline positive control, zero runtimes or startup/memory changes.
See [authentication ownership evidence](../investigations/SWIFTUI_AUTHENTICATION_OWNERSHIP.md)
for the later native login/root-restoration investigation.

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
