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
