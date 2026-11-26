# Local workspace and generated outputs

Keep the authoritative checkout in `streamside/repo/`, donors in `streamside/donors/`, compilers in `streamside/toolchains/`, and generated outputs in `streamside/artifacts/`. Set `STREAMSIDE_ARTIFACTS_DIR` to override the artifact root. Overrides resolving into Git are rejected.

Native IPA assembly defaults to `artifacts/native-frontend/<revision>-<proof>/`. Hosted component downloads and build tickets live in `artifacts/ci/<source-sha>/`. Use verified hosted Apple components with `--components`. See the [CI build guide](NATIVE_SWIFTUI_CI.md) and [quota-aware build commands](APPLE_BUILDS.md).

Retain the current device candidate, one useful device-confirmed rollback and their matching components. Keep deliberately selected historical controls and recovery packages outside the active build folders. Before removing superseded packages, preserve original manifests, source identities, checksums, test results and unique failure evidence. Keep raw reports and personal data in a private local archive. Ignore generated outputs and signing files inside the checkout.

See [documentation maintenance](DOCUMENTATION.md) and the [native-only cleanup record](../investigations/SWIFTUI_NATIVE_ONLY_CLEANUP.md).
