# Diagnostic infrastructure v1 — hardening and acceptance

Recorded 2026-10-26 on feat/modular-diagnostic-runtime. Governing completion
scope: [F1–F6 audit](DIAGNOSTIC_INFRASTRUCTURE_COMPLETION_AUDIT.md).
Required future capability: [secure configuration updates v2](SECURE_INVESTIGATION_UPDATES_V2_PLAN.md).
V1 is not the final diagnostic architecture.

## Status and evidence boundary

| Item | Status | Evidence / remaining boundary |
| --- | --- | --- |
| F1 resource/lifecycle safety | Implemented; focused host regressions pass | Native pressure/background events and pre-command checks, acknowledged cleanup, bounded ownership. Actual device memory/thermal/latency acceptance remains F5. |
| F2 loss and provenance | Implemented; focused and compiled-Hermes regressions pass | Separate frozen overwrite/saturation records, native capture metadata pinned before packets, old evidence unchanged after later selection/epoch/capture/Stop. |
| F3 export queue/lock contract | Implemented; production-path host facade passes | One immutable native copy and one worker/buffer; formatting outside report lock, main-only clipboard/share handoff, cancellation and text truncation tested. Actual share-sheet/UI behavior remains F5. |
| F4 registry/UI/authoring contract | Implemented/documented; host facade passes | Real compiled description/revision/compatibility/source shown. Authoring guide identifies actual profile and v2 trust/cache design; no updater implemented. |
| F5 integrated host gate | Passed locally; F5 as a whole remains OPEN | 220 tests: 218 passed, two Apple-only skips. Both pinned Hermes predecessors and ordinary native artifact verification passed. Device/Apple requirements below are not met by these results. |
| F6 milestone closure | PENDING | No supported-platform completion or release claim. Public feature/release reconciliation awaits F5 evidence. |

Build metadata advances to 3.1.0-build.25 / framework 3.1.0.25 to distinguish the
changed source/native artifact from build 24. This is an ordinary native build
for integration verification, not an installed/device-accepted candidate.
No IPA was generated, signed, installed, uploaded or published.

The selected immutable manifest is revision 5, numeric-chat-v4 /
rn-chat-current-v4, SHA-256
4cd52fba566b77f2b1fdfaaada48bb37c9b150f626c645d50f5f7a4faa4de965.
All limits are identical to revision 4, including the effective 2 ms snapshot
deadline, 128 shared entries, rates/rings/bridge/alias/report ceilings.
Runtime ABI1 and the three compiled capability versions remain unchanged.
The wire profile is versioned for one new numeric retention row, not new
observation coverage.

## F1 implementation and accounting

The [host](../../src/TASInvestigationHost.c) registers five fixed OS resource/
lifecycle notifications independently of the Investigations page. Delivery is
coalesced onto main; Arm/Capture also inspect current foreground/thermal state.
Serious/critical thermal state or background refuses new work. Memory warnings
stop the current collection. Recovery permits explicit Arm; it never rearms.

Native Stop now has a Stopping state until acknowledgment. Failed/expired
delivery becomes Unsupported, not a claimed successful Dormant teardown.
Generations reject stale Arm/Capture acknowledgments. Resource stops cancel
pending export formatting/handoff, retain frozen partial numeric evidence and
record a numeric stop reason. No synchronous entry into a stalled executor,
polling timer or functional state mutation was added.

Repeated state/client replacement can copy an owned wrapper into a new object.
The recorder now gives each arm a token, so copied wrappers from previous arms
remain inert. A weak ownership map recognizes an owned wrapper's original
function before wrapping it again. Original return/exception/context and
foreign ownership remain preserved. Tests run 100 copied-state/client cycles
with one original call and one observation per admitted action.

Owned resource accounting:

| Phase / object | Bound and lifecycle |
| --- | --- |
| Native numeric retention, prepared/frozen metadata and one export copy | 48,120 bytes measured by tas_inv_report_owned_bytes on this host, including two 640 × 9 × int32 row buffers and bounded metadata. Metadata structure is 664 bytes. Platform ABI sizes remain checked separately by native build. |
| Native report packet parser | At most 8 KiB input inspected transiently and 65 × 9 × int32 row scratch; no wire text retained. Eight packets / one capture; rate and generation enforced. |
| Export | One static 65,536-byte UTF-8 buffer; one pending worker/main handoff and three temporary retained UI objects. One NSString at handoff can require up to roughly 128 KiB of character storage plus platform overhead. Clipboard/share framework storage is not a measured diagnostic-owned heap result. |
| Manifest admission | At most 16 KiB input / 256 bounded tokens / depth 8; allocation-free native parser has about 71 KiB stack token storage. It runs at v1 initialization, not per message or while exporting. |
| Armed JS | At most 256 ordinary and 64 priority nine-number records; 256 total ID/nonce aliases and 65,536 logical UTF-8 alias bytes; object associations bounded/reset per scope; 16 current hook records, two live list/store records. No event bridge traffic or periodic scan. |
| Capture JS | Frozen history shares existing numeric row objects; bounded array/reference copies plus the shared 128 entry projections and at most two contexts. One capture timer only during bounded transfer. |
| Native resource/UI queues | One coalesced pending resource operation plus the executing one, one coalesced status operation, one command/probe deadline, one export job. No queue grows per notification, row or message. |
| Old copied/foreign wrappers | Weak ownership metadata does not strongly root old wrapper keys. Foreign code may retain inert forwarding wrappers; original functional ownership is preserved. Their runtime/GC lifetime still needs F5 measurement. |
| Startup source admission | One extra SHA-256 pass records the actually admitted patched HBC. Source graft/NSData/VM bootstrap allocations are bounded by the exact admitted bundle, but are much larger than active report buffers. Startup/donor-owned objects are not certified under a 512 KiB total-process claim. |

Native buffer counts and bounded-container tests establish structural ceilings,
not exact Hermes allocator overhead, Cocoa allocation size, retained
Twitch-object lifetime or a measured 512 KiB aggregate device bound. Those
performance/retention claims remain unproven pending F5. No existing resource
limit was raised to make tests/captures complete.

## F2 evidence contract

History freezes first. Kind 12 is placed in the first transfer immediately
after the frozen header; its a/b columns are ordinary/priority ring-overwrite
counts. Header admission skips, alias evictions, adapter errors and transfer
truncation keep distinct meanings. Saturation flags identify capped counters,
elapsed time and labels; capped values are not exact totals. Coverage means
adapters installed during the arm interval, not uninterrupted observation of
every scope or proof that all messages reached a lifecycle stage.

Before invoking Capture, native freezes the selected manifest revision/digest/
source, compiled capability/schema/profile identity, donor native UUID/text
fingerprints, original and admitted patched HBC identities, VM epoch, Arm
generation/sequence, independent general logging policy, selected limits and
monotonic Arm/Capture request times. First/last receipt times and interrupted
stop status are recorded separately. These are not an atomic JS/native time
or geometry claim.

No raw private identities/content are added. Unknown membership, unavailable
coverage and measurement/cache/zero distinctions remain unchanged. A later
Stop, rearm, source replacement or settings/configuration change cannot rewrite
an already selected export's identity.

## F3 and F4 completion

[Native report export](../../src/TASInvestigationReport.c) takes one bounded copy
under the report lock. Formatting and existing numeric summaries use that copy
without the live report lock. [UI export](../../src/TASInvestigationUI.c) uses a
single worker and a main-queue handoff; no clipboard/share UI runs on the
worker. New capture packets can arrive while export is pending. Repeated export
requests are refused rather than accumulating copies. Resource cancellation
suppresses a pending presentation without clearing captured evidence.

Numeric rows precede optional human-readable summaries. The global 64 KiB
ceiling is unchanged; text-limit exhaustion produces an explicit
EXPORT_TRUNCATED marker, preserving the retained numeric capture rather than
returning a silently empty report. This differs from transport truncation and
does not change complete/interrupted semantics.

The current UI reads the copied compiled configuration for description,
revision and status. [Diagnostic authoring documentation](../../diagnostics/README.md)
now describes revision 5, v4 profiles, existing runtime controls and the
separate required v2 milestone. No Refresh Registry control, fetcher, signing
key or mutable update admission was added. The current bundle's exact-byte
pin remains intact.

## Verification

Fresh host integration:

- Four focused hardening cases execute production C/JS paths: resource events
  without page creation, stale/failed cleanup, exact ring loss and copied-wrapper
  cycles, immutable provenance/export concurrency/cancellation, maximum text
  truncation, real worker/main handoff and compiled configuration footer.
- The complete suite ran 220 tests: 218 passed, Foundation and ImageIO skipped
  because Apple/Xcode is unavailable here.
- Pinned compiled Hermes executed both exact original and complete functional
  predecessors, including new hardening fixtures, unchanged scoped donor seam,
  actual getter mutation traps and existing recorder/viewport regressions.
- Ordinary framework/dylib builds and Mach-O/WebP/artifact receipts verified.
- Report and manifest sanitizer harnesses each passed 20,000 malformed cases
  under ASan/UBSan. LeakSanitizer initially could not run inside the tracing
  sandbox; the same binaries passed outside it. No sanitizer failure was
  bypassed by disabling checks.
- Generated registry, compiled-receipt freshness and identical old/new manifest
  limits are checked. Documentation/whitespace checks accompany the commits.

These checks do not execute UIKit/RCT on an iPhone or measure device heating,
keyboard focus, native share presentation or background/PiP neutrality.

Historical preservation: the exact previous compiled-Hermes receipt is copied
to diagnostics/validation/history/hermes-build24.json, SHA-256
8d267dbdf9de8302a43470c6bdc6f57a90005c56b06a65621e24b8051dce51db,
matching the build-24 artifact record and pre-hardening Git bytes. Existing
native build-24 outputs/receipts were copied intact to the workspace artifacts/
build24-native-archive before the ordinary native rebuild. Prior manifests,
IPAs, checksums and validation records remain unchanged.

## F5 device acceptance — OPEN

Device target supplied by the user: **iPhone 16 Pro, iOS 27.0.1**.
No current performance tooling, connected Apple host or physical device session
is available in this workspace. No device pass is recorded for this source.

Use the next ordinary Streamside development build containing this hardening;
do not make a diagnostic-only IPA or request another chat-gap reproduction.
Current build 24 can be a historical baseline but cannot accept F1–F4 code that
it does not contain.

Record each result as passed, failed, not run or not measurable:

- [ ] Record installed ordinary build/source/signing identity and device/OS.
- [ ] Launch offline, mount chat once, Arm later without reopening it; capture
      ordinary history/state, copy and share, Stop and continue in the stream.
- [ ] Exercise the advertised functional-emotes-on/off admission paths.
- [ ] Compare Dormant → Armed → Dormant under comparable busy-chat loads with
      a sustained armed interval; record durations and external CPU, memory/
      retention, stalls and thermal observations.
- [ ] Check visible keyboard, draft and selection preservation, touch
      pass-through, scrolling, accessibility and portrait/landscape.
- [ ] Exercise PiP/background/foreground and repeated Arm/Capture/Stop;
      collection must not silently resume after a stop.
- [ ] Check native stop states and partial/cancelled evidence through a safe
      available test boundary; do not heat the phone deliberately.
- [ ] Inspect ordinary/own/reward observations where available, explicit loss/
      coverage/partial markers, current-range/newest-tail status and provenance.
- [ ] Run available Apple Foundation/ImageIO gates on an Apple host, or record
      the exact remaining compatibility limits.

The original quantitative CPU/p95 and aggregate memory targets are not waived.
Unavailable measurements remain unproven. A same-build Dormant/Armed comparison
does not establish a runtime-omitted versus installed/dormant result. Do not
mark F5 complete or generate successive diagnostic candidates to conceal this
evidence boundary. Fix only a reproducible failed infrastructure acceptance
criterion, without new observation adapters or intermittent-gap investigation.

## F6 closure — PENDING

Once F5 evidence exists, reconcile the accepted supported scope with affected
feature/build/test/compatibility/troubleshooting/changelog documents under
[documentation ownership](../development/DOCUMENTATION.md). Preserve old
failures/artifact identities and the original F1–F6 audit. Record remaining
limitations explicitly. No push, merge, release or branch deletion is implied.

The required secure-update v2 milestone remains separately open at M0–M6.
Closing v1 must not state or imply that immutable pinning is the final
architecture or that newly reviewed configuration bytes are remotely
updateable today.

## Source/native provenance

Implementation source: d9317c52fac8916e1d0887bec1ba4cef5194d9c5.

- Ordinary framework SHA-256: 11c41e383062ad117f8f882f7c10b2d2312a447c777e4a3df825c8b298733a6c.
- Ordinary dylib SHA-256: f21082911849c3dff82da63959132c23034e06835b2eb71c0cd58532a1192195.
- Current compiled-Hermes receipt SHA-256: fd5caa5515c8e3f7a7762372d756d7219a5519f0054c134672747db652234cb8.

The workspace artifacts/v1-hardening-2026-10-26-validation.json binds the
source, native artifact/receipt digests, log digests and explicit pending-device
status. Persistent local logs are under build/v1-hardening-2026-10-26.
The final report-legend wording change was rechecked by all 27 focused cases,
both compiled predecessors, native verification and the report sanitizer;
the 220-case integration result is recorded separately without double counting.
There is no IPA or device acceptance artifact for this source.
