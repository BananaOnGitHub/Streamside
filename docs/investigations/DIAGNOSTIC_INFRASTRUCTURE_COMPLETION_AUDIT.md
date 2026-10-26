# Diagnostic infrastructure completion audit — 2026-10-26

The initial diagnostic platform is implemented far enough to capture and export
real device evidence. It is not yet fully accepted. The remaining milestone is
a finite hardening and acceptance pass, not finding the cause of RN chat gaps.
A report can be useful, partial and inconclusive while the platform works as
designed.

This audit freezes the remaining scope into six completion items, F1–F6 below.
No new diagnostic IPA, observation adapter, donor seam, Fabric probe or
chat-gap experiment is part of the audit. No production source or build number
was changed.

## Audited baseline and governing requirements

Audited checkout: feat/modular-diagnostic-runtime at
1d64187d87caf19ca6317f4a5eb09b4d9bf706cc. Build-24 implementation source is
365214477eab053134c852ee0d3c9ea80eace6d6. Both are based on
dev/3.1.0 at 0a3cf9603f8885d6c2d8433dded227698b047f20.
The working tree was clean before this audit.

The complete original inputs are retained outside Git in the local workspace,
under /home/bananas/Agent-Stuff/streamside/references:

| Reference | SHA-256 | Role in this audit |
| --- | --- | --- |
| investigation implementation(1)(1).md | b14d1850ea2ebb11e6a335777beccd6930c66e1fe74ef14737cbb00471512d90 | Original functional brief; sections 1–12 and Acceptance goal. |
| investigation implementation(1).md | 8afda0e34552f2460047b575c524b4e50702b357b14a171a5d34bf683c430c8b | Local implementation/recovery brief; sections 2–12 and final acceptance. |
| MODULAR_DIAGNOSTIC_RUNTIME_PROPOSAL.md | 36779fced095c425bd886a597dd7a9b3d149d2a6cfb8da6cead06a888464a580 | Architecture, trust, resource, snapshot and migration contracts. |

The implementation briefs override the proposal's snapshot-only first stage,
optional event history and 60-second armed lease. Event observation is required
in v1, and acknowledged Armed operation has no fixed session expiry.
The briefs explicitly allow a safely admitted subset of observation fields,
with unavailable coverage identified. They explicitly defer signed mutable
registry updates after the first proven runtime; the local brief requires
retrieval/cache design, not an unsafe update implementation.

Old document instructions to prepare successive candidates are historical
delivery context. They do not authorize continuing the gap-driven candidate
cycle in this audit.

The milestone being closed is **diagnostic infrastructure v1**: one admitted
runtime in ordinary Streamside development builds; the existing RN chat
profile; immediate runtime Arm/Capture/Stop; bounded prior history and current
state; honest local export; safe teardown; bundled offline configuration.
It is not the entire future capability roadmap or a complete chat delivery /
rendering observability system.

## Evidence categories

“Implemented” means production code exists. “Host verified” means executable
local tests or exact-donor Hermes replay, not iOS execution. “Device observed”
means the specific behavior was reported by the device user or appears in their
exported report. It does not certify untested behavior on the same device, a
later candidate, another signer or another donor.

The [implementation record](MODULAR_DIAGNOSTICS_IMPLEMENTATION.md) preserves
checkpoint history, startup failures, corrected fixtures, candidate identities,
normal-chat evidence and reported gap captures. Later acceptance must append
evidence; historical pending statements and old hashes must not be rewritten.

## Requirement-by-requirement status

| Requirement and source | Implemented / source evidence | Host verification | Device evidence | Remaining and milestone effect |
| --- | --- | --- | --- | --- |
| Native coordinator, one investigation, fixed capabilities; brief §§2–3 | [Core](../../src/TASInvestigation.c): descriptors, acknowledged state transitions, one pending command, generations, deadlines. | Native coordinator refusal/ack/timeout/cycle tests. | Dormant/Armed reported working after build 21. | Core exists; safety-stop completion is F1. No replacement architecture needed. |
| Exact native/Hermes admission and startup bootstrap; brief §2 | [Host](../../src/TASInvestigationHost.c), [graft](../../src/TASRNInvestigationPatch.h), source interception in [TASEmotes.c](../../src/TASEmotes.c). Main/React/Hermes UUID/text and exact source/predecessor checks; startup ping/ack. | Both original and complete functional predecessors; wrong inputs refused; actual donor factory/seam/getters executed in pinned Hermes. | Build-20 failure exposed a pre-ready JS exception; build 21 corrected globalThis binding. Later successful captures establish working live delivery on the reported device. | Real delivery is observed. Device behavior with functional emotes off and loss/re-admission paths is not established. F5 checks; no new seam. |
| Activate an already mounted list without rerender/remount; brief §2 | Stable scoped ref seam, two bounded live list/store records; no added React component or setter on Arm. | Late activation with no intervening render, original ref/cleanup/error identity, 100 cycles. | User can arm and capture in the running stream. Independent mount counts were not measured. | Do not upgrade reported success into proof of every neutrality property. F5. |
| Dormant operation; brief §3 | Registration only; no recorder polling timer, full-chat scan, per-message bridge or serialization. Runtime is linked by the ordinary [build](../../build.sh). | Dormant fixtures, static command/timer paths and source checks. | No measured dormant CPU, allocation or thermal acceptance record. | Implementation present; quantitative overhead / retained-lifetime acceptance remains F5. |
| Long-running event recorder; brief §§3–4 | [Investigation.js](../../src/rn/Investigation.js): 256 ordinary / 64 priority rows, token/work admission before label allocation, no armed expiry or armed timer. | Simulated >2-hour session, saturation, callback preservation, repeated teardown, private-string sentinels. | Build-22/23 reports contain pre-capture translation/emission/store events and one reward-store route. Reports cover short arm intervals, not an extended performance run. | Core is working. Ring-overwrite accounting is missing, F2; device sustainability is F5. |
| Event-family coverage; brief §4 | Translation, emission, unpublished local echo, aggregate store notifications, IRC reward route, direct reward-store route and list lifecycle. Family mask is recorded. | Owned wrappers executed; originals, returns, exceptions and context preserved. | Mask 375 and selected events observed. Not every route is individually device-validated. | Lightweight subset meets the brief's conditional coverage rule. Per-message dedup/filter, confirmed reconciliation, reward renderer/catalog and row-layout probes are not completion blockers. |
| Original callbacks and hook ownership; brief §§4,9 | Temporary descriptor restoration only while still owned; original calls and thrown values forwarded; scoped subscriptions removed on Stop. | Foreign replacements preserved; original cleanup and 100 repeated lifecycle cycles. | No independent device leak/ownership stress record. | Existing implementation retained. F5 validates normal Stop/background behavior; F1 covers resource stops. |
| Freeze before snapshot and retain partial history; brief §3 | First transfer freezes and sends history before current getters; numeric native retention survives interruption/Stop. | Snapshot failure, cancelled capture, ordered parts, timeout/partial report and stale callbacks tested. | Completed normal/gap captures contain both history and state. | Works in observed success paths. Keep this invariant through F1–F3; do not require every capture to be complete. |
| Read-only bounded snapshot; brief §4 | Current list/store, known-size map, direct positions and donor viewport. Safe getter graph; no elementAtIndex/sizeAtIndex. | Exact donor getters with deep mutation traps; shared 128-entry / 2 ms deadline; zero, unmeasured, invalid, unavailable and changed states. | Build 23 sampled all eight reported visible rows plus the available margin. Cached heights/positions were observed. | Safe subset is implemented. Native pixel geometry, “ever measured” history and Fabric content are unavailable by design, not blockers. |
| Viewport priority / recent store traversal; proposal snapshot contract | Build 23 samples visible rows then two-row margins. Build 24 reverses existing bounded store traversal and adds examined/bounds/stop flags. | Actual owned compiled payload, deadline-before-tail, failed newest read, entry/time stops, changed and alias-limited cases. | Viewport projection confirmed in build 23. Newest-first build-24 traversal has no device report. | Build 24 is host verified only. F5 can check ordinary capture output; no gap reproduction or standalone diagnostic IPA is required. |
| Identity and conservative membership; brief §§3–4,9 | Bounded private aliases; numeric per-arm labels; complete comparable stable scans required for absence. Partial/unread remains unknown. | Alias bounds, privacy sentinels, partial/changed correlation and export summaries. | Actual reports contain ephemeral labels and unknown partial memberships. | Retain semantics. F2 supplies complete provenance/loss interpretation; missing observations never become a dropped-message claim. |
| Performance/resource safety; brief §§3,8 | Rate/count/byte limits, measured JS admission work, callback deadline checks, bounded queue/capture/cooldown. Individual already-entered getters cannot be preempted. | Mock-clock bounds, saturation and native parser limits. Aggregate peak owned memory and actual iPhone perturbation are not established. | Two individual snapshots recorded about 1.7–2.0 ms; this is not CPU/thermal acceptance. | No thermal-state or memory-warning stop exists. Genuine blocker F1; real sustained overhead acceptance F5. Do not raise budgets. |
| Stop, background, VM invalidation; brief §9 | JS ingress stopped on Stop delivery; owned work/aliases released; generations reject stale results. Native VM/source invalidation. Background/scene Stop is currently registered by the UI. | Stop/cancel/re-admission and overlay teardown facades; native coordinator generation tests. | No full background/PiP/repeated-stop acceptance record. | Put safety lifecycle ownership in the runtime, independent of page creation; exercise preservation and stale work in F1/F5. A stalled executor cannot be synchronously preempted. |
| In-place capture action; brief §5 | [UI](../../src/TASInvestigationUI.c): opt-in non-key scene window, button-only hit region, capture before reporting UI, no transcript insertion. | Settings dismissal, hit testing, native layout/rotation and teardown in a UIKit facade. | Button works in chat, survives landscape; Capturing returns to Capture. | Keyboard/draft/selection, VoiceOver, real touch pass-through and PiP neutrality not established. F5, not a new control design. |
| Parser, trust and offline configuration; brief §6 | Strict bounded native parser, allowlisted capabilities, exact-byte SHA pin, bundled manifest revision 4. Optional identical-cache-byte validation API. | Invalid/duplicate/unknown/type/depth/UTF-8/integrity/limits cases; invalid-cache fallback. | Captures identify the configured digest. Network-off launch not separately recorded. | Bundled offline operation is implemented. No disk cache, fetcher or signed update path exists. Retrieval/cache design and honest UI scope are F4; mutable updates are deferred, not silently claimed. |
| Investigations settings; brief §7 | Arm, Capture, Stop, in-chat button, copy/share, runtime status, actual native state/reason; general presets remain separate. | Host state/UI facade; no preset dependency in production commands. | Controls and Copy Capture used successfully. | Compiled manifest description and revision/source/availability are not surfaced as required. Small UI completion in F4. No multi-investigation browser is needed for the single supported profile. |
| Self-contained report provenance; proposal report identity | [Report](../../src/TASInvestigationReport.c) currently includes build/donor text, ABI, manifest digest, capture generation/sequence, coverage/loss/truncation rows. | Numeric parser and bounded formatter tests. | Those fields are present in supplied reports. | Missing explicit manifest ID/revision/source, capability versions, original/admitted HBC identity, VM epoch, capture-pinned policy/limits and interval metadata. Genuine evidence-contract gap F2. Do not read mutable “current” state when exporting an old report. |
| Loss accounting; brief §3 | Admission skips, alias evictions, adapter errors and transfer truncation are recorded. Ring replacement is bounded. | Saturation proves capacity, not exact overwritten counts. | Header skip counts observed. | append replaces old ordinary/priority entries without overwrite counters. Genuine requirement gap F2. No existing skip count measures message loss or ring overwrites. |
| Local bounded export; brief §§7–9 and proposal command/queue contract | Copy/share only on explicit action, one numeric native report, 64 KiB UI buffer; no automatic upload. | Parser hostility, privacy and output tests. | Copy Capture works. Share-sheet export not separately confirmed. | export_report calls formatter synchronously on the UI path; formatter holds the native report lock through summaries/text generation. Genuine queue/work separation gap F3. |
| Build/recovery/regression gates; brief §§10–12 | Ordinary build includes runtime and rejects stale compiled-Hermes receipt. Historical branches/manifests/artifacts retained. | Existing build-24 full suite and native/package verification. Receipt fingerprints current source. | Packaging is not device acceptance. | F5 reruns gates once after the finite code batch; F6 documents supported scope. No push/merge/branch deletion is required for closure. |

## What genuinely blocks completion

The source gaps are limited to F1–F4. F5 is an acceptance-evidence gate,
and F6 records the resulting supported contract. Missing measurement is not
implemented behavior; pending device evidence cannot be closed by more host
tests or package checks.

In particular, all of these are **outside the completion list**:

- Identifying or fixing the existing chat gap, missing-message symptom or
  composer behavior. A reproducible normal capture is sufficient to verify
  infrastructure transport and snapshot contracts.
- Adding native/Fabric text observation, renderer/catalog hooks, per-message
  filtering/deduplication, new reconciliation probes or additional row geometry.
  Their unavailable fields remain explicit.
- Making every store/list scan complete. Honest partial coverage within the
  unchanged budget is correct behavior.
- Composer, image, playback or other capability migrations; extra Twitch
  donors; multi-investigation leases.
- Signed mutable registry updates, key rotation, rollback infrastructure,
  GitHub transport and persistent downloaded-manifest caching. These are
  separately scoped future work explicitly deferred by the briefs.
- The proposal-only first-time, dormant “activate and capture” shortcut.
  This is a declared design omission: the implementation brief's acceptance
  flow explicitly arms before reproduction, and v1 closes that flow. Do not
  describe the separate first-symptom shortcut as implemented.
- Revalidating every historic candidate or rewriting old investigation records.

The pinned registry has a material limit: **different configuration bytes
cannot currently be delivered to this runtime without a new trusted build**.
Arming/capturing compiled capabilities does not require another build.
This satisfies the original first-runtime trust scope, not the eventual
“reviewed configuration updates without an IPA” vision. Copying the same
pinned bytes from GitHub would not remove that limit and is not a completion
feature. If that future update vision becomes a required milestone, it must
be named separately rather than claiming immutable pinning implements it.

## Resource-envelope differences from the proposal

The proposal's numeric envelope was explicitly provisional. The current
manifest/code differs in several visible respects: 256/64 retained ordinary/
priority records instead of the proposed 64/32, rates 8/4 per second instead
of 2/2, a 3-second native capture cooldown instead of 5 seconds, and a
64 KiB wire ceiling instead of the proposed 32 KiB. Per-packet 8 KiB and
4 batches/s remain bounded. The snapshot uses one checked synchronous read
pass with an effective 2 ms budget rather than the proposal's cooperative
32-entry / 1 ms target chunks; already-entered getters are not preemptible.

These are implemented parameter/design choices, not measurements proving
equivalent perturbation. Their safety remains subject to F1 accounting and F5
device acceptance. Preserve the current limits during closure; do not silently
claim the original numeric targets were all implemented, and do not enlarge
them to improve completeness. The armed 60-second lease and snapshot-only
prototype are different: the briefs explicitly superseded those two choices.

## Fixed completion plan

Implement F1–F4 as one coherent local source batch, with focused tests per
change. Then run F5's integration gate once. No intermediary IPA or symptom
hunt is part of these steps. Preserve the current 2 ms snapshot work allowance,
128 shared entries, event/bridge rates and strict donor admission.

### F1 — Finish resource-safety and lifecycle stops

Status: missing source behavior / acceptance evidence. Blocks closure.

Use native event notifications and a current-state check when arming/capturing
for serious/critical thermal state and memory pressure. Refuse unsafe new work
and stop active collection, cancel owned work, preserve frozen evidence and
state a fixed numeric reason. Runtime lifecycle protection must not depend on
the Investigations page being created. Preserve the UI's independent overlay
removal.

Use the existing command/generation/cleanup path. Do not poll resource state,
add a message hook, change chat state or synchronously enter a stalled JS VM.
Stop is best effort until the executor processes it; pending/failed cleanup
must not be presented as successful teardown or silently resumed. Foreground
return does not automatically rearm.

Account for peak owned buffers/copies/queues and bounded references across
Dormant, Armed, Capture and Export; document the aggregate memory envelope
and verify repeated cycles do not accumulate owned resources. Underlying
Twitch-owned objects are not an unlimited diagnostic retention allowance.

Done when: host tests cover unsafe initial state, pressure while armed and
capturing, background before/after page creation, preserved partial report,
stale acknowledgments, failed command delivery, store/client replacement across
repeated cycles without duplicate owned observation, and explicit rearming after
recovery. Resource counters/copies have a bounded accounting record. Device
perturbation itself remains F5.

### F2 — Finish loss accounting and capture-pinned report identity

Status: incomplete evidence contract. Blocks closure.

Add saturating ordinary and priority overwrite counters at ring replacement.
Keep overwrites separate from admission suppression, alias eviction, adapter
error and transport truncation. Define whether a coverage mask means adapters
installed during the arm interval or currently verified coverage; never imply
uninterrupted observation from an accumulated installed-family bit. Freeze these counters with history; disclose
counter/time saturation rather than treating a capped value as exact.
Retain the existing coverage limitations and unknown-membership rules.

Freeze the metadata needed to interpret each capture: manifest ID/revision/
digest and bundled trust source, compiled capability/schema versions, admitted
native/donor and original/patched HBC identities, VM/arm/capture generations,
general logging policy separately from the investigation, activation/capture
intervals and actual selected limits. Use existing admitted/coordinator facts;
do not introduce new app observation fields or retain raw private identifiers.
Explicitly identify unavailable metadata. Old reports must remain tied to
their captured configuration after Stop, rearm, host replacement or settings
changes.

Done when: exact saturation/overwrite tests pass for both rings; a frozen
report exported after those state changes retains its original identity and
limits; max-occupancy privacy/byte-bound tests and partial-report cases pass.
No report claims complete event history from transport complete=1.

### F3 — Finish bounded export without blocking UI or report ingress

Status: export works, work placement is incomplete. Blocks closure.

Take one bounded immutable native copy of the selected report and its F2
metadata under the lock. Release the lock before correlation/formatting.
Run those operations on one bounded worker; reject/coalesce repeated export
requests rather than queueing unlimited copies. Only final clipboard/share UI
presentation returns to the main queue. Count the copy/buffer in F1's envelope.

Keep the same 64 KiB global report ceiling. If output will not fit, retain useful
numeric evidence with an explicit truncation marker rather than silently
presenting an empty export. Capture/Stop can continue without waiting on text
formatting, and an export must never combine two captures.

Done when: production-path tests verify worker/main separation, short lock
ownership, concurrent capture/Stop, one pending export, stable snapshot identity,
bounded maximum-size output and no automatic presentation/upload.

### F4 — Close the built-in registry/UI contract and authoring boundary

Status: pinned implementation exists; required presentation/design unfinished.
Blocks the stated interface/documentation contract, not a remote-update build.

Display the compiled description and built-in revision/source/compatibility
status on the current Investigations page. Keep Arm/Capture/Stop separate from
general presets and make the absence of mutable updates explicit.

Complete the promised retrieval/cache design in the owning diagnostic authoring
documentation: fixed repository/revision/path policy, original-byte digest
checks, size/depth/time/redirect/path limits, one explicit refresh in flight,
verified atomic cache policy and offline fallback. Clearly mark this as a
future transport design with no runtime fetch/cache implementation. Do not add
a cosmetic Refresh Registry button or a pretend updater.

Document which changes are already runtime controls, which existing parameter
changes a future trusted manifest could select, and which new fields/hooks/
donors still require compiled code. Require a capability version change for a
semantic expansion. Retain exact admission and immutable revision history.

Done when: UI/source tests show real built-in revision/description/status;
documentation matches the actual parser/available profiles and describes the
future trust boundary without implying network functionality. Existing bundled
offline operation remains independent of networking.

### F5 — One integrated host gate and one device acceptance pass

Status: host foundations strong; final device acceptance incomplete.
Blocks an unqualified supported-platform completion claim.

After F1–F4, rerun the affected native and JS tests, pinned compiled Hermes on
both predecessors, donor getter mutation traps, original five-stage/emote/
WebP/legacy/VAFT regressions, sanitizer gates, receipt freshness and native
artifact checks. Record failures/skips accurately. Apple-only verification is
not established by Linux facades; run available Apple gates or retain a
specific compatibility limitation, not a fabricated pass.

Use the next ordinary Streamside development build for the final device pass;
do not package another diagnostic-only IPA to chase a gap. Current build 24 can
supply baseline evidence for unchanged paths, but cannot validate F1–F4 code
that it does not contain. Its newest-first store traversal is still host-only.

Bound the device pass to these explicit checks:

1. Launch with networking unavailable, open chat, arm after it has mounted and
   capture ordinary traffic. Export history plus current state, Stop and keep
   using the same stream. Test functional emotes on/off when that advertised
   path is exercised; never change them as a prerequisite for activation.
2. In a single representative session compare the same build Dormant → Armed →
   Dormant under comparable busy-chat loads, including a sustained armed interval.
   Record duration, device/OS/build, process CPU, memory/retained growth, stalls
   and thermal behavior using external tools where available. Do not add an
   internal sampler. Record which quantities could not be measured.
3. Check capture with a draft/selection and keyboard visible; touch pass-through,
   scrolling, rotation/landscape, accessibility and PiP/background/foreground.
   Check no unexpected keyboard dismissal, draft/selection loss, reconnect,
   remount symptom or automatic rearming.
4. Repeat Arm/Capture/Stop and confirm ordinary/own/reward observations where
   available, partial/budget markers and newest-entry traversal status. Validate
   the F1 stop behavior through the available safe test boundary; do not heat a
   phone deliberately to force a thermal notification.

No waiting for a chat gap is required. No blank-row root cause, exhaustive
coverage or guaranteed full scan is an acceptance criterion.

Pass criteria are recorded successful controls/cleanup, correct evidence
statuses, bounded stable retention, no significant heating/stalls or changed
functional behavior attributable to arming/capture, and measured overhead
within the declared targets. The proposal's ≤1 percentage-point process CPU
increase and ≤0.2 ms p95 added callback work are acceptance targets, not existing
results. A same-build Dormant/Armed comparison does not establish the separate
“runtime omitted versus installed/dormant” CPU claim. Report that claim and any
unmeasured p95 value as unvalidated; do not invent a result or require another
special IPA merely to label it passed. A narrower accepted scope must say
exactly which performance guarantees remain unproven.

Required sustained performance and UI-neutrality acceptance is not waived by
this audit. If the evidence cannot be obtained, F5 stays pending with the
specific missing input recorded; another diagnostic build is not the fallback.

If this pass reveals a reproducible infrastructure defect, fix only that
failed acceptance item and rerun the affected check. Do not reopen capability
scope or add observers to explain unrelated Streamside bugs.

### F6 — Record feature freeze, integrate normal use, close the milestone

Status: pending F1–F5. Required closure record.

Reconcile the supported implementation with [diagnostic feature documentation](../features/DIAGNOSTICS.md),
[building](../BUILDING.md), [testing](../development/TESTING.md), compatibility,
troubleshooting and the changelog where affected, under
[documentation policy](../development/DOCUMENTATION.md). Remove stale current
claims such as the authoring README's revision-2 summary; preserve historical
per-build evidence in place.

Publish one supported-scope statement, the completed F1–F5 checklist, source
revision, test/device evidence and explicit remaining limitations. Document the
routine flow: use the ordinary development runtime, arm an existing built-in
investigation, capture/export locally, stop. New capabilities are separate
Streamside work, not unfinished tasks on this milestone.

No merge, push, release publication, branch deletion or historical artifact
replacement is implied. A local milestone can close with preserved commits
and evidence. Mark this checklist complete only after its acceptance conditions
are met; once closed, unrelated chat-gap diagnosis is regular Streamside work.

## Verification performed for this audit

Fresh checks on 2026-10-26:

- 23 focused investigation tests passed, zero skips: native parser/coordinator,
  report transport/formatting, startup dependency facade, overlay facade,
  source viewport regression and validation-receipt tests.
- Compiled-Hermes receipt freshness and generated registry checks passed.
  This checked existing proof against current source; it did not rerun Hermes
  or execute iOS.
- Source inspection confirmed ordinary runtime inclusion, absence of pressure/
  thermal handlers, missing ring-overwrite counters, export queue/lock behavior,
  and missing report/UI provenance fields.

Existing build-24 records were inspected, not newly claimed as today's runs:

- Full suite: 216 tests, 214 passed, two Apple-only skips (Foundation/ImageIO).
- Pinned compiled Hermes on both exact predecessors and audited getter graph.
- 20,000 report mutations and 20,000 manifest cases under ASan/UBSan.
- Verified native framework and IPA with preserved donor identities.
- No build-24 device acceptance.

Documentation/whitespace checks are recorded with the audit commit. No new
native artifact, IPA, runtime instrumentation, version bump or chat-gap
experiment was produced. The remaining work is exactly F1–F6, subject only to
fixing failures of those stated acceptance criteria.
