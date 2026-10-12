# Building Streamside

Ordinary native builds cross-compile the checked-in C/runtime sources with Zig. Private donor analysis is not required just to build the native artifacts, but is required for validating RN bundle changes or preparing a compatible patched IPA.

## Prerequisites

- Zig **0.14.0**, the version used by CI.
- Python **3.10+** for build, packaging, and tests.
- The checked-in runtime headers/link stubs and a POSIX shell.
- Node for the JS fixture tests that use it.
- For an IPA: a compatible decrypted arm64 Twitch input.
- For the Apple HTTP cache gate: macOS with Xcode command-line tools/`xcrun`.

The build uses the Objective-C runtime and explicit blocks, with `-Wall -Wextra -Werror`. It does not require an injected donor framework runtime for initialization.

## Ordinary build and checks

```sh
make verify
make test
make deb
```

For a Zig binary outside PATH:

```sh
ZIG=/path/to/zig make verify test
```

`make verify` builds and checks both artifacts:

- `build/Streamside.dylib` and its `.macho.json` receipt.
- `build/Streamside.framework` and adjacent `Streamside.framework.macho.json`.

`build.sh` normalizes segments and signature layout before recording fingerprints. The jailbreak dylib reserves 64 KiB for replacement signing; the framework uses compact signing metadata and the exact framework loader identity.

The complete gate/evidence distinctions are in [Testing](development/TESTING.md). Ordinary tests can skip platform/private-input checks; a skip must be reported.

## Prepare an unsigned IPA

Both routes below patch a compatible decrypted Twitch IPA with Streamside. Run the commands from the repository root. The difference is whether Streamside is built and tested first.

### Build, test, and patch with `make ipa`

Use this when preparing an IPA from source, especially after changing Streamside:

```sh
make ipa INPUT_IPA=/path/to/Twitch.ipa OUTPUT_IPA=/path/to/Twitch-Streamside.ipa
```

The Makefile runs these steps:

1. `build.sh` compiles the framework and dylib and records their fingerprints.
2. `artifact_guard.py` checks both built artifacts (`make verify`).
3. `make test` runs the ordinary test suite.
4. `patch_ipa.py` inserts `build/Streamside.framework` into the input IPA.
5. `verify_ipa.py` independently opens and checks the saved output IPA against that framework.

Build, test, or verification failures stop the target. This command runs the ordinary test suite; the mandatory Apple Foundation and compiled RN validation gates remain separate where required, as described in [Testing](development/TESTING.md).

### Patch with an already-built framework

Use `patch_ipa.py` directly when you already have a verified framework and want to patch an IPA without rebuilding Streamside or rerunning its tests:

```sh
python3 tools/patch_ipa.py /path/to/Twitch.ipa \
  --framework build/Streamside.framework \
  --output /path/to/Twitch-Streamside.ipa
```

The script checks the supplied framework against its fingerprint receipt, patches the app, and verifies the temporary output archive before saving the final filename. It does **not** compile source, check a separate jailbreak dylib, or run the test suite. After source changes, it still uses the framework you supplied; it does not rebuild it or check that it reflects those changes.

To repeat the finished IPA check explicitly, run:

```sh
python3 tools/verify_ipa.py /path/to/Twitch-Streamside.ipa \
  --framework build/Streamside.framework
```

Both routes produce an unsigned IPA for the chosen installation tool to sign. Neither installs the app, creates a tag, or publishes a release. The patcher refuses encrypted/malformed inputs, removes historical injected components, inserts one required Streamside framework load, and preserves unrelated entries.

Keep `Streamside.framework.macho.json` next to `Streamside.framework` when moving a built framework. The receipt must match its exact binary and metadata; a filename/version label is not an integrity receipt.

## Required compiled RN validation

RN library changes and donor ports must run the actual Hermes/donor gate, not just JS facade fixtures:

```sh
TAS_RN_DONOR=/path/original.hbc \
ZIG=/path/zig \
TAS_HERMESC=/path/hermesc \
TAS_HERMES_SNAPSHOT_RUNNER=/path/hermes-build/bin/streamside-snapshot-runner \
TAS_HERMES_SOURCE=/path/hermes \
make test-rn-virtualization
```

The pinned runtime source revision is `40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c`. Build its runner using:

```sh
python3 tools/build_snapshot_runtime.py \
  --source /path/hermes --build /path/hermes-build \
  --cmake /path/cmake --ninja /path/ninja
```

The analysis parser setup must support Hermes-98's inspected large-header/exception metadata. Set its package path as required by the verifier. See [Twitch internals](development/TWITCH_INTERNALS.md) and the [compiled baseline](archive/investigations/EMOTE_DEMAND_PHASE1B_CALCULATION.md#reproducing-the-compiled-test).

The validator regenerates/checks payloads, executes the production graft, checks donor registration/settings and unchanged RN window functions, and writes local `build/snapshot-validation.json` evidence with input/compiler/runner fingerprints.

## Diagnostic variants

```sh
EMOTE_DIAGNOSTIC=1 make verify
IMAGE_DEMAND_DIAGNOSTIC=1 make verify
```

Each flag accepts only 0 or 1. Normal builds use zero. Image-demand diagnostic builds require a current passing compiled snapshot record **before** cross-compilation. Missing/stale/failed evidence stops the build; a generic host skip cannot bypass that guard.

`RN_SNAPSHOT_VALIDATION` can select the record path. Do not distribute a diagnostic build under an ordinary release label without documenting its probes.

## Local bundle preparation

`make deb` prepares rootful/rootless DEBs and verifies their archived dylib bytes. `make release` runs verification/tests/DEB preparation and creates a local developer ZIP/checksums. Neither creates a GitHub release, tag, or public asset.

Public IPA and `-jb` package distributions remain separate. See [Packaging](development/PACKAGING.md) for artifact preparation and binary contracts.

## Paths and cleanup

Relevant build variables include `ZIG`, `ZIG_LIB`, `IOS_STUBS`, `ZIG_LOCAL_CACHE_DIR`, and `ZIG_GLOBAL_CACHE_DIR`. Use task-specific paths for caches when needed.

`make clean` removes the repository's generated `build` and `dist` directories. It is not needed for documentation review and should not be run in a worktree containing artifacts that need preservation.

[Contributing](../CONTRIBUTING.md) · [Packaging](development/PACKAGING.md) · [Testing](development/TESTING.md)
