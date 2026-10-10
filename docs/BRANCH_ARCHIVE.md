# Archived branch: archive/rn-image-demand

Closed at the user's request on 2026-10-10. This preserves the entire
`diagnostic/rn-image-demand` history plus documentation-only closure.
The original implementation head is
`7f48f67ea9ee3273f6c312587fafac6e077b10ec` (build 87). All implementation and
shared closure documentation are incorporated by fast-forward into
`compat/twitch-31.5`; this archive adds only its own README notice and this note.

## Purpose and completed work

Investigated excessive provider library startup demand, cache admission delays
and bounded queue overflow without replacing Twitch's image decoder or RN
window algorithm. Builds 73–77 added passive demand and calculation probes;
build 78 fixed fractional-column interval endpoints and retained a confirmed
virtualization regression baseline. Builds 79–82 added independently bounded
cache-first delivery, a real Foundation cache/revalidation gate, conservative
eligibility diagnostics and network-proven receipts for eligible Date-less
entries. Build 83 added bounded overflow recovery without throughput changes.

The user observed legacy UIKit player/chat on vertical-enabled streams. Builds
84–85 investigated blank native Recent on first opening; build 86 corrected
premature gap placement while sections were still absent. Build 87 corrected
stale emoji tint at section handoff and delayed footer insertion after keyboard
reparenting. The user confirmed both legacy fixes work.

## Outcome and retained decisions

The [shared branch closure](DIAGNOSTIC_BRANCH_ARCHIVE.md#rn-image-demand-builds-73-87)
records the complete milestones, report deltas, validation and evidence limits.
Warm E→F reuse added 197 direct hits with no additional network transactions;
that does not establish that earlier 1–5 second waits were harmless. The
performance architecture is frozen. Revisit throughput only if device behavior
demonstrates a remaining bottleneck; overflow recovery remains independent.

Report version `3.0.0-build.87` and bundle version `3.0.0.87` are unchanged by
archive closure. Source, tests and full ancestry are retained. No new IPA,
release or additional device result is claimed by these documentation commits.

## Evidence

- [Passive demand](EMOTE_DEMAND_PHASE1.md)
- [Startup demand investigation](EMOTE_DEMAND_PHASE1B.md)
- [Compiled calculation and build-78 baseline](EMOTE_DEMAND_PHASE1B_CALCULATION.md)
- [Cache-first transport and overflow](EMOTE_IMAGE_TRANSPORT.md)
- [Legacy picker fixes](LEGACY_RECENTS_DIAGNOSTIC.md)

Continue current work on
[compat/twitch-31.5](https://github.com/BananaOnGitHub/Streamside/tree/compat/twitch-31.5).
