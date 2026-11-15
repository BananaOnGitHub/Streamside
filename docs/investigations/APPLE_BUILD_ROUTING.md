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
