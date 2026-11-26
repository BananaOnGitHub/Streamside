# Native-only branch and artifact cleanup

The working tree started clean on `feat/native-frontend` at `eb4d30f761e75921913451293b76a92d39eaa2d5`, including the device-confirmed chat composer. The exact tree was published separately as [archive/pre-native-only](https://github.com/BananaOnGitHub/Streamside/tree/archive/pre-native-only) and verified against the remote before removal. The [immutable checkpoint](https://github.com/BananaOnGitHub/Streamside/tree/eb4d30f761e75921913451293b76a92d39eaa2d5) contains the RN tweak, UIKit recovery prototype, diagnostics, prior release workflows and documentation. Main and existing development and archive branches are preserved.

## Active native tree

- `native/` contains SwiftUI, the native C/Objective-C ABI adapters, pinned donor admission and original-startup guard.
- Shared VAFT and its diagnostic headers now live in `native/shared/`. Its host and Apple transport tests remain active.
- `tools/native_frontend/` builds and verifies donor-free SwiftUI components and packages the donor locally. The package output defaults to a flat native-frontend directory keyed by source and proof. Framework metadata is shared by component compilation and assembly.
- Linux CI runs donor-free host tests. The Zig cross-compiler and Unicorn still validate native ABI boundaries. Private-donor inspection tests run locally.
- Hosted Xcode still validates native account, playback, profiles, chat, model and simulator behavior and the baseline control. The old tweak's Foundation provider-cache fixture, Hermes snapshot tooling and release/deb packaging live at the archived checkpoint. The native Foundation playback transport tests remain.
- Native investigations, failure evidence, licensing and current build guidance remain in the branch. Historical references to retired source use the checkpoint's immutable revision.

The SwiftUI-only bridge removes the old UIKit follows query and initialization path. The active native feed, session lifecycle, playback and RN/Hermes/worklet measurement remain. The full Ubuntu test set passed 172 tests, including actual donor admission. Fresh Apple compilation and device regression checks are pending.

## Local retention

The [compact identity inventory](evidence/native-only-cleanup/package-identities.json) records all 34 original package manifests and 69 CI directories, including recorded SHA-256, source revisions and validation states. Every IPA was measured against its original manifest before retirement. The current composer and previous avatar IPA, their matching components, the historical independent baseline and legacy recovery package are retained.

The local private archive `artifacts/archive/native-only-cleanup/evidence.tar.gz` contains 736 original evidence files, including raw reports, manifests, build/validation logs and failure archives. Each member was verified against its original SHA-256. Archive SHA-256 is `0a8b5c566d9cf42056de542c63d35e3392baebda8f55525f1335530301bfabeb`. Its adjacent private inventory records original paths and identities. Raw reports remain local.

The removal inventory covers 32 superseded IPAs and 67 superseded CI directories, including the old nested `swiftui/` directory. Generated payloads are retired only after the compact inventory and archive are preserved.
