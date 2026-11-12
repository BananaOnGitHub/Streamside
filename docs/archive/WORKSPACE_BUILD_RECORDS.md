# Recovering retired workspace build records

Raw build output and the obsolete R5 binary-staging utility were removed from the
active tree after a successful hosted SwiftUI build. They remain in published Git
history and the annotated tag `archive/workspace-build-records-2026-11`, targeting
`1a1459a4626c71d570dd3c850c5215099fe651a7`. No history was rewritten.

[The recovery inventory](WORKSPACE_BUILD_RECORDS.json) records every retired path,
size and SHA-256. It covers the 161 verbatim workspace record copies, raw cleanup
logs, the former local workspace note and `tools/stage_r5_production.py`. Original
source revisions, failed compiler attempts and build identities remain recoverable.
Compact manifests, artifact inventories, summarized validation outcomes and the
original signed-in/signed-out device evidence stay in the current tree. Required
generated C headers and runtime validation receipts remain active build inputs.

Browse [the preserved workspace evidence](https://github.com/BananaOnGitHub/Streamside/tree/1a1459a4626c71d570dd3c850c5215099fe651a7/docs/investigations/evidence/workspace-history)
or [the historical R5 utility](https://github.com/BananaOnGitHub/Streamside/blob/1a1459a4626c71d570dd3c850c5215099fe651a7/tools/stage_r5_production.py).
For an isolated local recovery, run from the current checkout:

```sh
git fetch origin tag archive/workspace-build-records-2026-11
git worktree add --detach ../artifacts/workspace-history-recovery archive/workspace-build-records-2026-11
```

The recovered checkout contains historical procedures and machine paths. It is a
reference, not the normal build environment. R5 reproduction still requires its
exact historical donor and explicit `--historical-reproduction`; current packaging
uses the maintained source-backed builders. See [the tooling audit](../investigations/SWIFTUI_CI_AND_TOOLING_AUDIT.md)
and [current SwiftUI build guidance](../development/NATIVE_SWIFTUI_CI.md).
