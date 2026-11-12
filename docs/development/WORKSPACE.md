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
must also be outside the checkout. Use `--frontend swiftui --apple-build-host tahoe`
for the configured Apple builder, or `--frontend uikit --zig /path/to/zig` for the
preserved UIKit path. Keep the Ubuntu checkout authoritative; only the explicit
Apple build-input allowlist and build outputs cross to the Apple host.

Retain current device candidates and useful rollback packages under separate
artifact directories. Before removing superseded binaries, commit their original
build manifests, source identities, checksums, test results and unique failure
records. Git stores source and compact evidence; donor packages, generated IPAs,
compiler installations and caches stay outside Git. A source revision and hash
record preserve provenance, but do not promise a byte-identical future rebuild.

See [documentation maintenance](DOCUMENTATION.md) for evidence ownership and
[the cleanup record](../investigations/WORKSPACE_CLEANUP.md) for historical paths.
