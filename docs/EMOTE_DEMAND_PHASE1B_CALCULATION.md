# Build 75: targeted RN startup calculation trace

Parent: diagnostic build 74 plus its device findings, commit
`66d8b8b46b3eeebc6faabb4fcccd8ede83b2d9b8` on
`diagnostic/rn-image-demand`. This is one diagnostic build, not a rendering fix.
Compat, transport, caching, queue admission, concurrency and capacities are
unchanged. The library's props, columns, source values, image types, animation,
keys, callbacks and window calculations remain unchanged.

## Exact boundary and bounds

The diagnostic-only `LibraryColumnsTrace` obtains the owned horizontal
FlatList's `_listRef` through its ref callback. It shadows
`_adjustCellsAroundViewport` only on the first two owned list instances in the
launch. Donor function 25830 implements that boundary; state updater 45709
invokes it from 40828. It receives the actual props, previous range and pending
update count used by RN, and calls the original method exactly once with the
original receiver and all arguments. The original result object is returned
unchanged; original exceptions propagate unchanged. No donor function body,
prototype, global RN export or other list instance is patched.

During that synchronous call only, a forwarding observer on the same list's
`_listMetrics.getCellMetricsApprox` observes frames the original method actually
queries. Each real query executes exactly once and returns its original frame.
There are no extra metric queries, replays of the algorithm, second downloaders
or image requests. The observer compares up to 64 actual queries per adjustment
with the pure owned column `getItemLayout` callback. Its four samples are the
first four distinct queried catalog-column indices; repeated indices consume
no sample slots. It does not inspect emote names, source URLs or item identities.
The temporary observer is restored in `finally`, including exceptions.

Capture ends at **five seconds, 128 adjustment calls or 16 distinct numeric
snapshots**, whichever comes first, for each of two owned instances. Identical
numeric snapshots are suppressed. The deadline is not extended by scrolling or
renders. The instance method is restored at the limit, ref detachment or
component cleanup. Inherited methods are restored by deleting the shadow; own
methods regain their original value. Restoration never overwrites a method
that another actor replaced meanwhile. A stable diagnostic ref callback avoids
reinstalling the trace on ordinary rerenders. Missing/incompatible boundaries
produce an unsupported counter and leave the original method untouched.

The native report retains two fixed sixteen-row numeric arrays, approximately
11 KiB total; it rejects oversize, malformed, non-finite or late-stage packets.
Numeric JSON is transient and never retained as a string or treated as an asset
fingerprint. The report buffer is 32 KiB and the host fixture verifies the last
row and following report content remain present when both slots are full.
There is no unbounded per-open, per-item or per-image history.

## Reading a calculation row

| Field | Interpretation |
| --- | --- |
| list / transition / stage | Anonymous first or second instrumented owned list, bounded snapshot order and existing lifecycle stage; no session or channel identity |
| prev / result | Actual prior and returned cells-around-viewport ranges at one synchronous boundary |
| viewport / content | Internal visible length and content length captured before the original calculation |
| zoom code / value | Zero, unit, positive non-unit, negative, missing or non-finite; invalid numeric values use -1 |
| offset / velocity | Offset sign only; velocity direction only outside the unit threshold; invalid values have a distinct code. No scroll coordinates retained |
| pending / catalog | Actual pending count passed to the method and actual `getItemCount(data)` |
| initial / batch / window | Actual props forwarded by FlatList, not the configured values inferred from source |
| branch | 1: window algorithm; 2: dimensions not positive; 3: pending update; 4: virtualization disabled, matching donor 25830's branch precedence |
| nested / layout | Actual same-orientation nesting predicate and presence of `getItemLayout` |
| queries / invalid / mismatch | Actual metric query count; invalid geometry and >0.5-point disagreement with owned geometry in the first 64 observed queries |
| cell samples | Column index and actual length/offset, compared with owned length/offset; -1 indicates missing/invalid data. These are geometry, not emote identities |

This observes the final adjustment boundary, not RN's individual binary-search
comparisons or every intermediate render mask. It does not claim pixel
visibility or native image attribution. If the first observed previous range
is already full and no expanding transition is captured, that explicitly limits
the evidence: the ref installed after that expansion, or the retained state was
already large. Do not infer the missing inputs from later geometry. If a limit
is reached before the expansion, do not infer that RN stayed bounded. Exceptions,
unsupported boundaries and packet refusals are reported separately.

The existing build-74 aggregate telemetry remains available for cross-checking
the committed image population and render mask. Diagnostic observation adds
bounded JS/bridge overhead; this build is evidence about the calculation, not
a performance benchmark. Production without `bridge.observe` retains the
original unwrapped FlatList path.

## Short device pass: two reports

1. Restart Twitch once. In the same large-catalog channel, open the library
   for the **first time**, stay stationary for ten seconds and capture **A**.
2. Scroll horizontally once. Close the library, reopen it on the same channel,
   stay stationary for ten seconds and capture **B**. Do not restart Twitch or
   change provider/scope filters between A and B.

There is no need for a baseline, separate scroll report or ten-stage pass.
Opening another library or changing filters before this sequence may consume
one of the two instrumented instances; the report says how many were installed.
Clearing the text log does not reset the fixed startup capture.

## Validation

94 host tests passed. Production owned-wrapper fixtures verify unchanged
receiver/arguments/result/frame identity, exactly one original call/query,
same-instance rerenders, distinct branch and non-finite classifications,
duplicate snapshot suppression, both bounds, inherited/own method restoration,
original exception propagation, deadline restoration, active dismissal,
idempotent cleanup, unsupported getters and the uninstrumented third instance.
Production C fixtures verify fixed slots/rows, numeric validation, privacy,
full report delivery and memory bounds. Existing library, chat, composer and
shared transport fixtures also pass. These fake RN calculations do not prove
the real device's cause or mount bound.

Exact Hermes-98 graft verification preserves all 47,322 donor functions;
124 owned strip functions / 25,944 bytes. The iOS diagnostic framework build
and unsigned IPA verification pass. Adding `_strtod` to the link stub exposes
the existing system numeric parser used only by this diagnostic packet reader.
No cache-first, queue-overflow, retry or artificial-window-clamp changes are
included. Phase 1B remains open until the device calculation explains the
expanded first-open range. Phases 2 and 3 remain separate.

## Build 75 device results: A and B

The two supplied reports reproduce the expanded range but do **not** capture
the calculation snapshots needed to explain it.

| Observation | A: first stationary opening | B: after scrolling and reopening |
| --- | --- | --- |
| Library openings | 1 | 3 (two reopens, aggregated) |
| Library JS instances live / launch peak | 837 / 837 | 837 / 837 |
| Open or reopen stage mounts | 837 | 1,674 across two reopens |
| Open or reopen maximum range / mask / catalog columns | 168 / 168 / 168 | 168 / 168 / 168 |
| Inner viewport / content width | 370 / 10,360 points | 370 / 10,360 points |
| Maximum viewable columns | 7 | 7 |
| Calculation installed / restored | 1 / 1 | 2 / 2 |
| Finished calculation calls / snapshots | 24 / 0 | 60 / 0 |
| Unsupported observations / packet refusals | 24 / 0 | 61 / 0 |
| Foundation transactions: network / local cache | 0 / 851 | 0 / 2,647 |

B's 2,856 cumulative mounts are not simultaneous views: 2,019 have unmounted,
leaving 837. Its scroll stage unmounted 1,052 and mounted 345; close released
another 967 library instances and 44 recent instances across the recorded
closings. Reopen mounted 837 images per opening. The closing counts establish
cleanup, while reopening again expands to the full catalog. The bounded
reopening seen in build 74 was not reproduced in this run. Neither the precise
range-expansion condition nor a reason for that difference is established.

Every recorded Foundation transaction in this run was a local-cache response.
All task completions and local-cache fetches were within 250 ms after admission.
B's queue waits were 2,548 within 250 ms and 99 within one second; none exceeded
one second. Library source-to-onLoad callbacks were 689 within 250 ms, 1,593
within one second and 574 within five seconds. These callbacks include downstream
RN/decode work; they are not network download measurements or direct pixel
display measurements. This run cannot establish cold-network performance or
the Phase 2 requirement to bypass an occupied network admission queue.

The calculation wrapper did install and observe actual calls, then restore
at its deadline. It retained zero numeric snapshots. Status 3 currently combines
diagnostic preparation/serialization failures with unsupported installation;
the extra unsupported observation in B is consistent with the third list being
outside the two-instance budget. With no packet refusals and zero JS snapshots,
the capture failure occurred before successful snapshot emission, not in the
native numeric packet reader. The reports do not expose the exact failing
expression. Inspection confirms the donor method's three-argument signature
matches the wrapper and the state updater passes props, previous range and
pending count in that order. Those checks do not resolve the runtime failure.

The host fixtures exercised source-level mocks; the graft verification exercised
bytecode structure and donor preservation. Neither executed this probe against
the device's RN instances. This is a validation gap in build 75, not evidence
that the calculation stayed bounded. The probe needs a narrowly validated
repair before another device pass can yield the requested inputs. More reports
from unchanged build 75 would not supply them. No speculative rendering fix,
additional IPA, cache change or queue change is made from these results.
