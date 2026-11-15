# Codemagic-preferred Apple build routing

## Implementation trial — 2026-11-15

Starting state: `feat/native-frontend`, clean commit
`5606baa79af95475d145a770f5abf98222a69e73`; published history is unchanged.

The manual fixed-source benchmark workflow is superseded by a current-source
Codemagic M2 workflow and Ubuntu dispatcher. GitHub's Apple workflow now runs
on explicit dispatch as the fallback, using the same shared Apple gates.
Linux/Zig and documentation workflows retain their existing triggers.
[Maintainer instructions](../development/APPLE_BUILDS.md) describe commands,
quota policy, local credential storage and failure recovery.

Read-only API validation established that the personal quota response uses
seconds: both allowance fields report 30,000 and both consumed fields report
660, corresponding to 489 free minutes remaining. No paid billing was enabled.
The new official OpenAPI provides build start/history/detail/artifact access but
has no free-minutes balance field; the legacy `/user` quota shape is explicitly
validated and any disagreement selects GitHub Actions. Raw account responses
and short-lived artifact links are excluded from committed evidence.

The selector's 25-minute initial estimate deliberately does not treat the one
11-minute benchmark as statistically conclusive. It reserves the full runner
timeout and a margin before admitting a free build. A local pending-submission
ticket prevents duplicate jobs following ambiguous network responses.

## Historical artifact retrieval follow-up

The previous benchmark record correctly reported a browser download block.
Ubuntu API retrieval now closes that limitation without changing the original
measurement: build `6af942e690e83b09c4fa7473`, configuration source
`567b2276e6e10c46b12d7ce790e7ff1de6693f26`, compiled source
`28eb9bc800865373e906ed28eab0f885ccc97331`.

Downloaded `Streamside_1_artifacts.zip`: 822,083 bytes, SHA-256
`0bfb9863947ec6c26ab2c62f1c4d6ca16ac9a49ca78d281838ec3730216d1dc4`.
The existing component admission validator passed source identity, generated
headers, exact toolchain, required test receipts and all component hashes.
External raw evidence is preserved under the existing benchmark artifact area,
`codemagic-01/api-retrieval/`; no generated files were added to Git.

## Validation status

Synthetic routing tests cover threshold admission, account-wide active-build
reservations, quota disagreement, unknown API responses, duration headroom,
uncertain submissions, duplicate prevention, exact source admission, redirect
protection and hostile archives. Live build validation follows in this record
when the current-source pipeline completes. No application UI/runtime code was
changed; new device validation is not claimed for build orchestration.

Official references: [REST API overview](https://docs.codemagic.io/rest-api/codemagic-rest-api/),
[OpenAPI schema](https://codemagic.io/api/v3/schema/openapi.json),
[pricing](https://docs.codemagic.io/billing/pricing/).

## Successful current-source end-to-end run

Implementation commit `ea9567b0c324efc1b60d67fe65b5ec5f3f248ab2` was pushed and
selected Codemagic with a verified 489-minute balance, 25-minute initial
prediction, and 50-minute admission requirement. Build
[`6af94f0790e83b09c4fa7689`](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6af94f0790e83b09c4fa7689)
finished successfully in **718.335 seconds** (11m 58s). The common component and
simulator suite took 671.866s; Foundation integration took 8.198s. The logger,
comparison and twelve routing tests also passed on the runner. The exact Xcode
and SDK pin was admitted by both component compiler receipts.

API download, bounded extraction and full component admission succeeded on
Ubuntu. All 51 post-download tests passed: 17 Apple-compiled ABI calls,
14 admission, 10 diagnostic core, one launch-policy, six probes and three
original-startup comparison tests. The pre-push native regression suite also
passed all 70 tests. Documentation checks and YAML parsing passed.

`streamside-components.tar.gz`: **833,713 bytes**, SHA-256
`fa6e31bb1274f3f11750c00348d69995ff6bd79f28988d261ba40aaa6349ac68`.
External artifacts and the resumable ticket are stored under
`artifacts/ci/ea9567b0c324efc1b60d67fe65b5ec5f3f248ab2/`, beside the checkout.
[Structured results](APPLE_BUILD_ROUTING_RESULTS.json) retain timings, receipt,
hashes, quota decision and validation scope.

Repeating `start` returned the same build ID. A live plan during execution
reserved 120 minutes for the unfinished account build. After completion the
account reported **477 free minutes**, one comparable successful sample, and the
same conservative 25-minute prediction. No token, donor or signing credential
was uploaded, and no VM connection was used.

The [Linux build](https://github.com/BananaOnGitHub/Streamside/actions/runs/43684935022)
and [documentation check](https://github.com/BananaOnGitHub/Streamside/actions/runs/43684934991)
passed. No duplicate GitHub Apple job was created. Insufficient/unknown-budget
fallback selection passed synthetic tests; GitHub's revised archive extraction
command was exercised against the actual downloaded archive and passed component
admission. A fresh full GitHub fallback Apple run was not performed in this
trial. Existing physical-device behavior is unchanged and is not revalidated by
these orchestration tests.

The maintained compilation guide now points to the selector instead of the old
automatic push/download flow. The fetch Makefile target adds the external local
test dependency directory; the existing pinned Unicorn 2.1.4 dependency was
preserved there from its prior temporary location. No generated build output was
moved into the source tree, and prior benchmark history remains recoverable.
