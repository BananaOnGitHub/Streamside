# RN transcript gaps and intermittently missing messages

## Scope

Read-only investigation against `a785256` on `dev/3.1.0` (3.1.0 build 6)
and the original Twitch 31.6 donor, build `262821841498166537`. The report
describes intermittent large spaces between visible RN messages and occasionally
invisible own messages. The installed build and device configuration were not
independently verified. The supplied screenshot is supporting visual evidence,
not a trace of message receipt, list contents, or cell measurements.

The screenshot shows separated visible rows. It cannot establish whether the
spaces contain invisible messages, stale reserved height, or unmounted cells.
It also cannot establish whether an invisible own message reached the server.
No screenshot, usernames, message text, or donor bytecode is added to this record.

No application behavior, build metadata, workflow, or repository settings were
changed by this investigation. No new IPA was prepared.

## Transcript list is not the emote library

The 31.6 donor's `ChatMessageListInner` is function 22318, exported by factory
4900 (Metro module 4896). It loads `LegendList` from dependency 17, module 4900.
At `0x1168` its list properties specify:

- `estimatedItemSize: 36`;
- `recycleItems: false`;
- `initialScrollAtEnd: true`;
- dynamic `data`, `drawDistance`, `keyExtractor`, and `renderItem`;
- end-scroll maintenance and content-size/viewport callbacks.

The corresponding 31.5 function 21887 also loads `LegendList` and has these
same explicit configuration values. This is not evidence of a newly introduced
list type or a newly enabled recycling setting in 31.6. The inspection does not
establish that the complete underlying implementation is unchanged.

The 7,344 scenarios in the retained compiled runtime gate exercise the emote
library's RN `VirtualizedList` window/overlap calculation, not this transcript's
LegendList measurement, mounted containers, or Fabric paragraphs. Those passes
do not validate this reported symptom.

LegendList has distinct position and size state (`positions`, `indexByKey`,
`sizes`, and `sizesKnown`). Functions 22388 (`resetLayoutCachesForDataChange`),
22392 (`updateItemPositions`), and 22418 (`applyItemSize`) identify useful
read-only measurement boundaries. These are candidates for observation, not
proven defective functions.

The library also contains a conditional measurement/reveal path involving
`experimental_hideItemsUntilMeasured`, `containerLayoutReady`, and container
generations. The transcript does not explicitly set that experimental property
in its inspected list-property construction; its final spread contains scroll
callbacks. The existence of the internal reveal path is not evidence that it
is enabled or responsible for these blanks.

## A row can fail independently

The donor's list render callback 38750 (`ze`) wraps each `ChatLine` in
`ErrorBoundary`, supplying `name: "ChatLine"` and `level: "error"`, without
an explicit fallback. Its dependency resolves through module 517's getter
7732 to module 551 and the `ErrorBoundary` export 8282.

That boundary's class render method 27215 checks `state.hasError`. On error it
uses `renderFallback` or `fallback`, otherwise returning null. Consequently a
row subtree can disappear while the rest of chat continues. An emote-rendering
exception could occur inside that subtree, but no such device exception was
captured here. Whether a null subtree retains a visible estimated/cached gap
depends on actual container measurement and subsequent updates; the screenshot
does not prove that sequence.

This is a concrete diagnostic boundary, not attribution to Twitch or
Streamside. A Streamside-induced render exception would still be caught by
Twitch's boundary.

## Receipt, local echo, and reconciliation

[The incoming hook](../../src/TASEmotes.c) calls its original WebSocket delegate
once with the rewritten frame or unchanged original. Refused provider matching
does not intentionally suppress the callback. Its counters do not establish
that Twitch accepted the resulting line into the store or mounted it visibly.

The [local-display patch](../../src/TASRNLocalEchoPatch.h) enriches only the
completed line's `emotes` array in function 35388, after translation and nonce
handling and before `emitLine`. Its 21-register call frame and isolated exception
handler remain present. Missing exports, refused matches, null additions, and
exceptions in added work resume the original emission. This does not rule out
an error later in rendering those additions.

The original donor also has several non-render admission boundaries:

- `translateChatMessage` 35392 can return null before the added patch runs;
- `pushLine` 45030 ignores an already-seen nonempty line ID;
- the store has hidden, paused, blocked-user, and delayed-message state;
- nonce reconciliation callback 48173 preserves an existing row key while
  updating the matching line ID;
- ordinary local-echo ID generation 35303 uses the client's `localEchoSeq`.

These are retained Twitch behaviors. No collision, invalid nonce, null
translation, filtering mistake, or lost own-message emission was reproduced.
An invisible own message may be a receipt/store issue or the same display issue
as the spaces; their relationship is not yet established.

## Streamside sizing scope and host checks

[The transcript width patch](../../src/TASRNWidthPatch.h) overrides width on
both inline wrapper and image for admitted provider aliases. It retains the
donor's height, baseline, and normal/enlarged branches. Extra width can cause
legitimate wrapping, so a layout interaction remains possible, but there is no
direct vertical-spacing override in that patch.

The cursor guard targets native composer selection requests; the popup adapter
targets the emote sheet; the library adapters target the picker grid/navigation.
None replaces this transcript's LegendList calculation or row renderer.

Checks run for this investigation:

```sh
ZIG=/path/to/zig python3 -m unittest discover -s tests -p test_rn_width.py -v
ZIG=/path/to/zig python3 -m unittest discover -s tests -p test_rn_incoming.py -v
```

All five width/local/composer-shim cases and all 15 incoming/local bridge cases
pass, with no failures or skips. These are controlled host/ABI/instruction
fixtures, not live UIKit/Fabric, transcript-store, or LegendList execution.
No new compiled Hermes runtime validation or device reproduction was performed.

## Next evidence boundary

A bounded diagnostic should correlate stages, without changing their outcomes:

1. Completed own/incoming line reaches original emission.
2. Store admits, reconciles, delays, filters, or deduplicates it.
3. Line appears in the transcript list's current data and render callback.
4. Its error boundary reports a render failure, or its container reports
   measured height, assigned position, mounted state, and viewport intersection.

Use launch-local opaque labels and small bounded samples. Do not record chat
text, raw message IDs/nonces, usernames, room IDs, image URLs, or exception
messages/stacks. Observe numeric error categories, own/provider/native flags,
counts, geometry, and original return outcomes only. Keep the transcript observer
separate from the emote-library calculation observer.

Until that evidence exists, do not disable virtualization, change row heights,
remove error boundaries, or alter deduplication as a speculative fix. A comparison
with an unmodified 31.6 client or a separate chat client can help distinguish
rendering failure from send/receipt failure, but no such comparison is recorded.

## Build 7 bounded trace trial

The diagnostic trial lives on `fix/rn-chat-gaps`, based on `a785256`
(3.1.0 build 6), with report identity `3.1.0-build.7` and framework build
`3.1.0.7`. It uses the same original Twitch 31.6 donor described above.
This is instrumentation, not a spacing, missing-message, or cursor fix.
The preceding read-only findings retain their original scope.

### Observations and boundaries

[ChatTrace.js](../../src/rn/ChatTrace.js) is an owned, diagnostic-only sixth
Hermes graft at the memoized `ChatMessageList` export in factory 4900.
It scopes observations to at most two chat stores encountered by the list.
The existing five-stage chain, donor list algorithm, filtering, deduplication,
translation results, original emission, error fallback, styles, recycling,
estimated item size, and scrolling configuration remain intact.
Context/probe components add no native views. Original callbacks, arguments,
return values, thrown objects, refs and ref cleanups are forwarded.
Diagnostic wrappers add overhead; this trial is not a performance comparison.

| Boundary | Observation |
| --- | --- |
| Translation | Returned line label or null-result count, including own-message null results |
| Emission | Entry, normal return, or numeric exception category |
| Store | Subscription snapshots, first observed membership, connected/paused/hidden/suspended state |
| List | First observed data membership versus first render-item callback |
| Row boundary | Numeric TypeError/RangeError/other category; no error message or stack |
| Geometry | Row local height/width/position and sampled native window rectangles; measured list viewport when available |

Raw IDs/nonces are correlated only in temporary JS maps, never sent to native
or written to the report. Reconciled IDs sharing a nonce retain their opaque
label. Reports contain session-local labels, counts, stage masks, flags, numeric
error categories and geometry—not chat text, usernames, room IDs, raw IDs,
nonces, image URLs, or exception text. The original report's other sections
retain their existing privacy rules.

[TASChatTrace.c](../../src/TASChatTrace.c) accepts exactly eight bounded JSON
numbers via the synchronous [trace bridge](../../src/TASChatTraceBridge.h).
Strings, objects, malformed syntax, nonfinite values and invalid schema/ranges
are rejected without retaining the input.

Bounds are two sessions, 256 labels/session, 512 ID and nonce aliases each,
256 store snapshots/session, scans of at most 2,000 entries, and 64 native
geometry requests/session. JS stops after 120 seconds or 1,500 packets
(plus at most two stop packets); native independently caps 1,536 packets
and refuses after 130 seconds from first acceptance.
Stopping unsubscribes and clears correlation maps, restoring only prototype
hooks still owned by this observer. Stable React wrappers remain inert until
process exit, avoiding a stop-triggered tree replacement.
The report prints at most 48 rows/session, prioritizing own, error, and
emitted-without-observed-store labels.

### Capture and interpretation

1. Install the unsigned trace IPA through the usual signing route. Keep
   Streamside's third-party emotes enabled, completely close the app, then launch.
2. Enter the affected RN chat directly. During the first two minutes in chat,
   send a few ordinary text/native/provider-emote messages and reproduce the gap.
   Avoid visiting unrelated rooms first; the first two encountered stores own
   the available session slots.
3. Copy the Streamside report from that launch and include whether a gap or an
   invisible own message was observed, plus Twitch/iOS/device and signing route.
   A fresh capture requires fully closing and relaunching the app.

The `RN chat trace` section shows per-session hook/subscription admission.
No session or `hooks=0/2` is missing instrumentation evidence, not a clean result.
Row stage masks use `1 << stage`; `list=1` means data membership, `list=2`
means a render callback, and `list=3` means both. Flags are unioned across
observations; state values and geometry are the latest sampled values.

A translated/emitted label absent from observed store or list membership can
narrow the next investigation, but does not prove a drop: batching, pauses,
filters, history windows and snapshot limits can explain absence. A row error
can explain the null fallback but does not establish who caused the error.
Window vertical overlap is not proof of painted pixels or an unobscured row.
Measurements can become stale during scrolling; recycled/unmounted ref
callbacks are discarded. The trace does not introspect LegendList's internal
size cache, intercept transport acknowledgments, or capture send-call admission.
Translation throws are forwarded unchanged without an added trace event.
Stage masks are accumulated observations, not a complete timestamped event log.
Later message arrivals, viewport changes, or a symptom after capture expiry
need a new run. Nothing here establishes device acceptance or attributes the
symptom to Twitch rather than Streamside.

### Host validation

The mandatory [compiled gate](../../tools/validate_chat_trace.py) regenerates
61 owned functions (9,636 payload bytes), applies the production C chain, and
admits only the exact predecessor footer/body and donor bindings.
Factory 4900 grows from 382 to 399 bytes, with frame 22 increased to 33 for
safe installer-call staging. Its guarded join preserves the original export
if installation throws. Final diagnostic HBC length is 28,734,704 bytes.
No unrelated predecessor function bodies, original literal buffers or debug
data are rewritten; original full-header offsets move with the enlarged table.

Both the owned entry and actual donor factory/export join run in pinned Hermes
through the production collector and RN handler, with mocked React, store,
native measurement and Objective-C boxing. Flow and limit fixtures pass for
both entries. The actual factory also retains its original export and style
initialization with a missing bridge or a throwing installer.
Five focused host tests cover packet rejection, limits,
privacy/correlation, callback/ref/error forwarding and stale/failed gate refusal.
The existing compiled library gate also passes: 32 accepted snapshots and
7,344 window calculations. Those remain library evidence, not transcript
LegendList or live Fabric evidence.

The full host suite runs 178 tests: 177 pass, zero failures, one Apple
Foundation/Xcode-only skip on Linux. Normal and trace builds pass both native
artifact contracts. A separate collector stress harness passes AddressSanitizer
and UndefinedBehaviorSanitizer on 20,000 malformed packets and truncated report
buffers. Its first run cannot execute LeakSanitizer because the environment
cannot read process-thread metadata; the successful rerun disables only leak
checking. Leak checking and real iOS/Fabric/RCTMethod behavior remain unvalidated.

Normal builds omit the trace graft and bridge; `CHAT_TRACE_DIAGNOSTIC=1`
requires a fresh compiled record before building. Local commands and gate
maintenance belong in [Testing](../development/TESTING.md#rn-transcript-trace-build).

### Candidate artifact

The trace candidate is
`Twitch_31.6_Streamside_3.1.0-build.7_chat-trace_unsigned.ipa`,
194,486,035 bytes, built with `CHAT_TRACE_DIAGNOSTIC=1`,
`IMAGE_DEMAND_DIAGNOSTIC=0`, and `EMOTE_DIAGNOSTIC=0`.
The independent IPA verifier confirms the unsigned app/framework contract.
It must be signed by the installation tool; no signing or on-device reproduction
was performed here.

- IPA SHA-256: `5eb2c5c0ab9a1de7a99c4421bee48d7947e57c7c956cb42a502e30ebaa3ba6f1`.
- Framework executable SHA-256: `d9a23b302c3f93bb968cac6d922ecc1af8a499529f11c769051a2b2ad3aa722d`.
- Six-stage in-memory diagnostic HBC SHA-256: `45f1901439c9dedaf76cc45e44d52ea64ff5f7c6dd2e50e015394373c486b618`.

These identities describe this trace candidate, not the preceding build-6
cursor candidate. The gap remains unresolved until a device report can be
correlated with an observed failure.

## Build 8 rolling trace trial

This follow-up on `fix/rn-chat-gaps` starts from `64dfd94` (build 7).
The supplied build-7 device report confirms that instrumentation ran, but
exposes capture exhaustion rather than a proven cause of the chat gaps:

- 1,502 packets, no native refusals, and `stop=2` in both sessions mean
  the JS lifetime event budget ended capture. The report has no elapsed
  capture timestamp; it does not establish when the visible symptom began.
- Session 2 reached all 256 store snapshots. Later labels still appeared
  in list data and render callbacks, so absent store-stage bits after that
  point are not evidence of actual message rejection.
- Only ten window measurements were accepted. Many async callbacks could
  be invalidated by a newly allocated context array even when the same row
  and native ref remained current. No row errors were observed during the
  retained capture; later errors remain unknown.

The device observation suggests possible onset after closing/reopening a
stream and possible worsening with time. Both are tentative observations.
The report cannot tie their timing to the old capture, establish progressive
layout corruption, or assign responsibility to Twitch or Streamside.
The original build-7 record, limits, validation and artifact hashes above
describe that candidate and remain preserved.

### Rolling retention

Build 8 removes the two-minute timeout and all lifetime packet, store-snapshot,
and geometry-request cutoffs. Sampling continues for the app process's
lifetime, including later stream reopening. It is still a diagnostic trial,
not a message, row-height, virtualization, deduplication or cursor fix.

The native collector retains the latest 2,048 events and a separate
128-event priority ring for own-message translation/emission, row errors,
list lifecycle changes and store retirement. Old events are overwritten;
the report states the retained elapsed-time range and overwrite count.
Retention duration depends on traffic and sampling, not a promised number of
minutes. Elapsed times use the native monotonic clock from first acceptance.
Copying the report creates a bounded snapshot without stopping capture.
Native memory remains fixed; input strings and arbitrary message data are
never stored.

The JS observer retains at most four stores, preferring inactive stores for
eviction and then the least recently accessed store. Eviction unsubscribes,
removes owned client mappings, clears caches and releases the store/probes.
An evicted store can be admitted later under a new opaque session number.
List mount/unmount effects emit lifecycle markers; reopening a retained
store increments its cycle and reattaches the subscription. These markers
describe the React list lifecycle, not a transport acknowledgment or proof
that a stream successfully opened.

Each store has bounded 512-entry ID and nonce alias maps, 256-entry stage
and own-label caches, and a weak object map reset at 256 new objects.
Raw aliases remain JS-only and rotate; eviction can relabel an older message,
so opaque labels are not permanent historical identifiers. Numeric session
and label allocation has a 10,000,000 ceiling; saturation yields unavailable
new labels/admissions and requires process restart, rather than reusing an
identity for a different message. Sample-frame numbers wrap at the same ceiling;
the much shorter retained window and lifecycle/elapsed fields scope comparisons.

### Sampling and loss reporting

The observer uses independent token buckets: ordinary flow/local-layout/ref
events replenish at 32/s (burst 32), native window sampling at 16/s (burst 24),
admission/coverage metadata at 4/s (burst 8), and priority events at 8/s
(burst 8). Full snapshot scans cannot exhaust the coverage-metadata lane.
Native independently limits regular
events to 64/s and priority events to 16/s. These are rate bounds, not lifetime
limits. Busy periods can suppress observations; the report explicitly records
loss counters and native schema/rate refusals.

One sampler runs every two seconds. Active-store order rotates for fairness.
Store snapshots no longer run on every row render; they sample up to 32
entries per store from a rotating scan of the first 2,000 entries. Observed
stage membership can refresh after ten seconds instead of remaining a
launch-wide one-shot assertion. List-data render observations sample the last
32 entries of that bounded range; original render-item callbacks remain
observed separately.

Each store retains at most 128 mounted row probes, sampling up to eight per
tick in rotation, plus its latest list viewport probe. At most 32 native
measurement callbacks may be in flight globally. A callback returns its slot
only once; a throwing request returns it immediately. Stalled callbacks keep
their slots rather than creating an unbounded native measurement queue.
Sample-frame records show the pending count; busy-slot skips are explicit.
Unchanged local layouts
are suppressed. A burst of local layouts cannot consume the native-window
sampling bucket. Row, native ref, lifecycle cycle and sample-frame checks
reject stale asynchronous callbacks; a harmless replacement of the context
array no longer invalidates a current row's measurement.

The ten-number wire adds lifecycle cycle and sample frame to the earlier
numeric schema. Reports group row evidence by session, label **and cycle**.
Window comparisons require matching row/viewport frames and cycles from the
latest observed sample, with separate measurement ages. Unobserved local
layout is explicitly marked unobserved. The latest 32 priority events and
48 geometry/coverage events are printed with elapsed times; ordinary summaries
show up to four recent sessions and 28 rows per session from at most 256
retained row/cycle keys. Display truncation is explicitly marked.

Coverage event 16 reports ordinary/geometry suppression, priority suppression,
probe eviction or measurement-slot skips, and alias/stage/object-cache turnover since the last accepted
coverage event. Native rate refusals are separate; bridge refusals also
contribute to JS suppression. Current prototype-hook ownership and subscription
availability are sampled repeatedly. The observer preserves a subsequent
foreign hook replacement instead of reinstalling over it.

Missing stages are **unobserved**, not dropped messages. Error masks, counts
and null-translation counts cover only the retained event window. The priority
tail may contain older evidence and is labeled separately. Geometry still
does not prove painted pixels, occlusion, LegendList cache correctness, or
send/receipt success. Multiple list views sharing a store use that store's
latest viewport probe; their geometry needs human interpretation, not automatic
cross-view comparisons. Background JS scheduling and delayed native callbacks
can also reduce coverage.

### Capture

Install/sign the new diagnostic IPA, keep Streamside's third-party emotes
enabled, and fully restart Twitch once to load it. Then use chat normally,
including closing and reopening streams. There is no initial capture deadline.
When gaps or missing messages appear, copy the Streamside report promptly
**before restarting Twitch**. The ring keeps recent evidence, not the entire
session. State whether the symptom followed reopening and whether it appeared
to grow; no exact onset time is required.

### Validation

The first updated regression run failed two native cases and one cap fixture
that still asserted the build-7 eight-number/lifetime-stop contract. Those
expectations were replaced with rolling-specific checks. This was a host
fixture-contract transition, not a device failure.

Six focused tests now pass, covering strict numeric rejection, bounded ring
overwrite, independent native rate limits, long-running capture, elapsed time,
late store admission/reopening, rotating labels, callback/ref/error preservation,
layout storms, privacy, and refusal of stale validation records. A geometry
fixture rejects cross-frame and cross-cycle overlap claims.

The shipped C graft and native RN handler execute in pinned Hermes through
both the owned installer and actual donor factory/export join. Flow and long-run
fixtures pass for both entries; the latter sends 3,000 messages before a late
reopen, using controlled JS/native clocks. They also verify that a foreign
prototype replacement is observed rather than overwritten. Factory fallback
passes with an absent bridge and a throwing installer.

The owned payload's regenerated identity is recorded with the candidate below. The factory join and
33-register frame remain unchanged from build 7; original predecessor bodies,
constant/literal buffers and debug data still pass preservation checks.
The separate library gate still passes its 32 accepted snapshots and
7,344 window calculations.

The complete host suite runs 179 tests: 178 pass, no failures, one Apple
Foundation/Xcode-only skip. Both normal native artifacts verify with the trace
omitted. The rolling collector passes AddressSanitizer/UndefinedBehaviorSanitizer
stress with 20,000 malformed packets, 5,000 valid events across eight numeric
sessions, ring overwrite and truncated report buffers. LeakSanitizer remains
disabled because of the previously recorded process-metadata restriction.
These are controlled host/runtime checks; live iOS/Fabric/RCTMethod acceptance
and a captured reproduction of the gap are still pending.

### Rolling candidate identity

`Twitch_31.6_Streamside_3.1.0-build.8_rolling-chat-trace_unsigned.ipa`
is 194,490,755 bytes, with report build `3.1.0-build.8`, framework build
`3.1.0.8`, and the same original Twitch 31.6 donor. Build flags are
`CHAT_TRACE_DIAGNOSTIC=1`, `IMAGE_DEMAND_DIAGNOSTIC=0`,
and `EMOTE_DIAGNOSTIC=0`. Both diagnostic native artifacts and the
independent unsigned IPA verifier pass. This candidate is not signed or
device-accepted.

- IPA SHA-256: `515b723f5f29385a3a3f9885bc141f57f10d11faee988dee43abf1a1b2119040`.
- Framework executable SHA-256: `cde925151792c5ab454dbdd00c0d50e437f72d07146ecbf917d4d2d044bccee5`.
- Owned payload: 78 functions, 14,208 bytes.
- Final six-stage diagnostic HBC: 28,739,480 bytes, SHA-256 `77117499e3f6116a4001866885ad2ebbe96493d2b0bd5ba7a5f2fc3f31d9799b`.

These are new artifact identities. The preceding build-7 hashes and device
capture findings are not reinterpreted as evidence for this candidate.

## Build 8 device capture and redemption investigation

The subsequent device report identifies `3.1.0-build.8` and the same Twitch
31.6 donor. The rolling observer remained active for 131.8 seconds, accepting
4,603 packets with no native schema refusals or native rate refusals. Its
ordinary ring retained 2,048 events from 74.5 to 129.4 seconds, overwriting
2,555 older events; 15 priority events survived separately. This establishes
live observer and native measurement activity for this run, not a chat fix or
general device acceptance.

The priority tail records the first list unmount at 42.0 seconds, a second
store/list mount at 44.2 seconds, and its unmount at 129.4 seconds. Two store
sessions do not identify two symptom incidents. Full first-session evidence
has aged out. Successful own-message translation/emission is preserved at
23.3, 63.2 and 82.7 seconds. Those events establish completed function calls,
not receipt, display, or which messages were missing.

The retained second-session summary contains no row-error events and no null
translations. Coverage events still report JS suppression and alias/cache
turnover. Missing render/layout observations, including for own-message labels,
remain unobserved rather than proof of a drop. Flags combine observations over
time; a paused bit on one label is not a claim that the entire run was paused.

### Geometry interpretation

The printed native samples contain these contiguous blocks within individual
frames and lifecycle cycle 1:

| Frame | Labels | Sampled vertical positions and heights |
| --- | --- | --- |
| 40 | 267–270 | `342/40`, `382/40`, `422/34`, `456/40` |
| 41 | 274–277 | `501.67/40`, `541.67/40`, `581.67/40`, `621.67/40` |
| 42 | 283–285 | `656.67/40`, `696.67/40`, `736.67/40` |
| 43 | 271–274 | `-212.67/40`, `-172.67/40`, `-132.67/40`, `-92.67/40` |

These blocks do not contain a measured gap between their sampled rows. Frame
43's rows are outside its sampled viewport. Do not compare positions across
frames to infer a gap: scrolling, viewport changes and unsampled intervening
rows prevent that conclusion. Only eight of 48 registered probes were selected
per printed frame. Several labels have identical duplicate measurements in
the same frame; probe counts are not counts of unique messages. The capture
does not determine whether those probes belong to nested hosts or separate
views. Local/window geometry also does not establish painted text or images.

### Redemption routing and a silent empty-render condition

Exact donor inspection distinguishes two redemption routes:

- IRC `custom-reward-id` messages become `channelpointsreward` events in
  `handleMessage` (35931). `onChannelPointsRewardEvent` (35389) calls
  `translateChatMessage`, attaches the reward identity, then calls `emitLine`.
- `useSynthesizedRewardNotices` (22060) subscribes to reward and celebration
  PubSub topics. Callbacks 38552/38553 create a `channelpointsreward` line with
  an empty body and pass it directly to the store's `pushRewardRedemption`
  (45065). This bypasses the two prototype methods observed by build 8.
  Store/list sampling can still observe the line, but the report does not
  classify its type or record the reward lookup result.

`ChatLineComponent` (22068) dispatches reward lines to
`ChannelPointsRewardLine` (22089), exported by Metro module 4790/factory 4794.
The renderer looks up `rewardsById[event.rewardId]`. For ordinary redemptions
without animation/celebration effects, the controlled renderer cases show:

| Inputs | Renderer result |
| --- | --- |
| Empty or whitespace body; missing reward definition | `null`, without an exception |
| Empty body; known reward definition | Reward notice view |
| Nonempty body; missing definition | Chat message row, without the reward header |
| Nonempty body; known definition | Reward notice and chat message |
| Deleted, empty-body line | `null` |
| Deleted, nonempty-body line | Chat message renderer, without the reward header |

With a stable event and retained compiler memo cache, supplying the missing
definition restores the notice; removing the definition returns it to `null`.
This is not evidence of a permanently cached empty render.

`useChatData` (21772) supplies the map via `buildRewardSnapshotMap` (20059),
which indexes automatic/custom reward definitions from settings. Reward updates
also have a separate Apollo/PubSub cache path. The device report contains no
catalog/query status or redemption classification, so it cannot establish
whether a definition was actually missing, a subscription failed, a notice was
filtered, or no redemption occurred during its retained window.

The silent `null` result is a concrete explanation for how a redemption notice
can be absent with zero row errors. Its connection to the reported blank spaces
is still a hypothesis: neither this fixture nor the sampled report proves that
LegendList retains space for such a line on the device.

### Streamside checks and reproducible evidence

The seven inspected reward bodies (4794, 22060, 22089, 35389, 38552, 38553,
45065) are byte-identical before and after the six-stage build-8 patch chain.
The IPA carries the original donor bundle; these patches are applied in memory.
The [reward investigation utility](../../tools/investigate_rn_rewards.py)
reproduces the recorded patched-HBC identity and runs the actual reward factory
and renderer on both original and patched bundles. The
[owned fixture](../../tests/fixtures/rn_reward_render.js) uses host dependency
adapters, not a replacement implementation of the renderer.

Eight render scenarios and a stable-event catalog arrival/loss sequence pass
on both bundles in pinned Hermes. An initial memo-identity assertion failed
because the host adapters supplied fresh Intl/attachment objects on each call;
stabilizing those adapter identities made the retained-cache check meaningful.
No donor renderer change was needed.

The additional [incoming transport regression](../../tests/test_rn_incoming.py)
passes exact-byte checks for `custom-reward-id` before and after the emote tag,
with proportional aliases both enabled and disabled. `NOTICE`/`USERNOTICE`
objects and non-IRC PubSub-socket frames retain their original identity.
All 16 tests in that native transport module pass with its existing
AddressSanitizer/UndefinedBehaviorSanitizer harness. This verifies Streamside's
rewrite boundary, not Twitch's downstream delivery or server subscriptions.

The full host suite runs 180 tests: 177 pass and three environment-dependent
checks initially skip. The two donor/runtime checks then pass when rerun with
the available exact-donor and pinned-Hermes inputs. The Apple Foundation/Xcode
check remains skipped; there are no failures. Documentation validation passes
for 73 Markdown files and 717 explicit references. Production source, version
metadata, the build-8 artifact and workflow configuration are unchanged.

Run the optional donor investigation with the parser environment and pinned
runtime prepared as described in [Testing](../development/TESTING.md):

```sh
python3 tools/investigate_rn_rewards.py \
  --donor /path/to/original/index.ios.bundle \
  --hermesc /path/to/pinned/bin/hermesc \
  --runner /path/to/pinned/bin/streamside-snapshot-runner \
  --runtime-source /path/to/pinned/hermes \
  --zig /path/to/zig
```

This utility is deliberately pinned to the recorded 31.6/build-8 identities.
It does not run in ordinary CI or change release/build gates. Private donor
bytecode and disassembly are not checked into the repository.

The next useful device observation must distinguish reward lines from ordinary
chat and record, numerically, catalog lookup presence and renderer `null` versus
element outcomes. It must include the direct PubSub/store route. Those facts,
aligned with list measurements and explicit coverage loss, can test the
redemption hypothesis without retaining reward IDs, titles, users, or chat
text. No behavioral fix or new app artifact accompanies this investigation.
