# Local workspace and generated outputs

Keep the authoritative Git checkout in `streamside/repo/`. Keep donors in
`streamside/donors/`, reusable compilers in `streamside/toolchains/`, and generated
outputs in `streamside/artifacts/`. Do not put build directories or build-directory
symlinks in the checkout.

Build and packaging tools default to the sibling `../artifacts/` directory,
regardless of the current working directory. Set `STREAMSIDE_ARTIFACTS_DIR` to an
absolute external directory to override it. Overrides resolving into the checkout
are rejected. Ordinary build products and caches use `artifacts/build/`; release
packages use `artifacts/dist/`. CI uses a directory in the runner temporary area.
`make clean` removes those two generated subdirectories, leaving retained device
candidates elsewhere in `artifacts/` intact.

The native frontend builder defaults to
`artifacts/native-frontend/<frontend>/<revision>-<proof>/`. An explicit `--output`
must also be outside the checkout. For SwiftUI, use verified hosted Apple
components through `--components`; see [the CI build guide](NATIVE_SWIFTUI_CI.md).
Ubuntu owns source, donor inspection, orchestration and local IPA assembly;
Codemagic or GitHub-hosted macOS runners own routine Apple compilation, selected
through the [quota-aware build commands](APPLE_BUILDS.md). An explicit
`--apple-build-host` is optional fallback for a configured Mac. No VM or SSH alias
is assumed available. The UIKit checkpoint remains buildable with `--frontend
uikit --zig /path/to/zig`. Reusable compilers are selected with `ZIG` or PATH;
per-machine installations and SSH configuration remain outside Git.

Retain current device candidates and useful rollback packages under separate
artifact directories. Before removing superseded binaries, commit their original
build manifests, source identities, checksums, test results and unique failure
records. Git stores source and compact evidence; donor packages, generated IPAs,
compiler installations and caches stay outside Git. A source revision and hash
record preserve provenance, but do not promise a byte-identical future rebuild.

See [documentation maintenance](DOCUMENTATION.md) for evidence ownership and
[the cleanup record](../investigations/WORKSPACE_CLEANUP.md) for historical paths.

Keep the artifact root indexed and compact: retain the current device candidate,
one device-confirmed native rollback, matching usable components, and deliberately
selected historical controls/recovery packages. Consolidate older raw reports and
failure evidence into a private archive with an inventory and verified hashes.
Do not publish raw device data merely to tidy local folders. Commit compact
original package metadata and meaningful findings before deleting superseded
packages; remove obsolete extracted products and regenerable caches afterward.
The [2026-11-15 cleanup record](../investigations/ARTIFACT_CLEANUP_2026_11_15.md)
records the retained candidates, archive and relocation map for this checkpoint.
