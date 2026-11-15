# Artifact cleanup — 2026-11-15

Starting state: clean `feat/native-frontend` at
`a22745a`, with 3,534 artifact files totaling **7,139,805,963 bytes** (6.65 GiB).
There were 35 IPA packages, mainly superseded native frontend iterations.
This is filesystem housekeeping; it does not change application code, donors,
reusable toolchains, credentials, published Git history or build selection.

## Preservation checkpoint

Before removing any source file, the cleanup created and read back every member
of a private local archive containing **577 evidence files**: original build and
compiler receipts, failure logs, device reports/screenshots, inspection records
and benchmark evidence. Its size is **8,183,917 bytes**, SHA-256
`ef2ba97378e176e5c7b8aa74f49e39f78132288c7c62ca056c855b72073b1c1d`.
Archive members retain their original paths relative to `artifacts/`.

The archive lives at `artifacts/archive/development-evidence-2026-11-15.tar.gz`,
mode 0600, outside Git. Raw device information and logs are not published.
Original package manifest data is preserved in
[package-manifests.json](evidence/artifact-cleanup-2026-11-15/package-manifests.json).
[The inventory](evidence/artifact-cleanup-2026-11-15/inventory.json) records every
IPA's size, SHA-256 and retention decision, the original source commit, archive
identity and relocation map. Original paths inside historical manifests remain
provenance, not current filesystem locations. Compact records are committed and
pushed before removing superseded binaries. Existing investigation results and
published source commits remain available.

## Retention and layout

- Current tags candidate: `native-frontend/stream-tags-b3fbef1/`, unchanged so the
  existing download link continues working.
- Last device-confirmed native rollback:
  `native-frontend/swiftui/player-shared-travel-28eb9bc/`, unchanged.
- Matching verified component directories for these two revisions remain in `ci/`.
- Independent historical Twitch 32 baseline moves to `archive/twitch32-baseline/`.
  Its original source is `1ca1414`; this historical control does not claim matching
  calibration for a newer native proof.
- Legacy build 24 IPA, native recovery products, testing notes and distribution
  outputs move together into `archive/legacy-build24/`.
- Tags inspection evidence and packaging log move into the current candidate's
  `validation/` directory.

The selection removes **31 superseded IPAs**, old extracted components and
regenerable Zig caches. It does not store those binaries in Git or claim that a
future recompilation will recreate identical bytes. The retained packages are
hash-verified against their original identities; archived evidence is verified
against each original file. An index in the artifact root identifies the retained
candidates and archive. No Apple build or VM session is needed for this cleanup.

Final removal totals and post-cleanup hash checks are recorded below after the
preservation checkpoint is published.
