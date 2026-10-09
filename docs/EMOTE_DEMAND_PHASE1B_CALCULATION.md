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

## Build 76 — snapshot pipeline validation gate

Build 75's zero snapshots remain a diagnostic failure, not an explanation of
168-column rendering. This repair separates twelve preparation steps into
attempted/passed/failed aggregate counters: props/catalog, content and scroll
metrics, numeric classification, base values, metric getter, observer install,
frame sampling, observer restoration, result values, frame packing,
serialization, and native delivery. No exception strings are retained. Sampling
failure remains distinct from real invalid/mismatched frame values. The native
five-argument `observe` export acknowledges event 27 only after its actual
bounded numeric parser and fixed snapshot store accept the packet. JS advances
the snapshot count only on acknowledgement; duplicate suppression follows
acceptance, allowing a failed diagnostic delivery to be attempted on the next
real calculation. No timer retries or image requests are introduced.

Host validation now executes the full production C graft chain in the matching
Hermes 98 runtime, revision `40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c`
(tag `hermes-v250829098.0.19`). Only the test bundle's global bootstrap is
substituted to expose the installer; every owned function body comes from the
shipped payload. React hooks/list state are fixtures, and platform object boxing
is a host adapter. JSI calls the same production `rn_demand_observe` handler,
export metadata, packet parser and report store used by the app. This does not
execute iOS Fabric, RCTMethod's Objective-C converter, Foundation, or actual
on-device layout. The host uses Unicode Lite and no Intl; numeric/ASCII packet
validation does not establish unrelated Unicode runtime behavior.

The compiled test produced 32 accepted 41-number snapshots across two owned
lists, including `viewport/content=370/10360` and `pending/catalog=0/168`.
All twelve failure-stage counters were exercised through the real generator.
Tests cover receiver/argument/result/frame identity, exactly one original
calculation per call, restoration after original exceptions, malformed packet
rejection, native delivery acknowledgement/refusal, duplicate suppression,
16-row caps, dismissal and timer cleanup. Existing Node contract tests retain
128-call and five-second lifetime coverage. Fixture result ranges are supplied
by a test calculation: they are **not** device evidence explaining 168 columns.

Executing the graft exposed a separate prerequisite that source mocks and a
valid disassembly had missed. Donor string ID 85127 (`remember`) has literal
kind, not identifier kind. Hermes fast property instructions require a
materialized symbol for their string ID. The assembler now inserts bounded
`LoadConstString` entry instructions only in owned functions that use a
literal-kind donor spelling as a fast property operand. Register zero is unused
at entry; frame sizes, outgoing-call register layout, original donor functions,
string/kind/hash tables and source property names remain unchanged. The complete
graft previously failed the host installer guard (and could produce an invalid
symbol); it now executes and passes native snapshot acceptance. This is not
proof that the same condition caused build 75's device snapshot failures: that
library successfully mounted, and its startup execution differed from the
isolated host bootstrap. The new failure counters address that remaining gap.

**Hard rule:** no diagnostic build or further device test until the compiled
snapshot pipeline validates for its current inputs. `build.sh` enforces this
when `IMAGE_DEMAND_DIAGNOSTIC=1`; missing, failed or stale validation records stop
the build. Even after host validation, the next device check is stationary only.
Do not request another full scrolling test until a device report includes at
least one accepted `calc list=... transition=...` row. If no row appears, inspect
the named failure counters before requesting more activity.

Short device check for build 76: restart Twitch, enter the same large emote
channel, open the library and leave it stationary for ten seconds, then collect
one report while still open. Close and reopen stationary for ten seconds and
collect a second report. No scrolling test is needed for this pipeline check.
If the first report has no accepted row, stop there and use its failure stages.

The donor's virtualization calculations, provider list props/keys, visible
window, catalog, transport admission, concurrency, queue limit, cancellation,
cache policy and HLS paths are unchanged. Full-chain verification compares all
47,322 preceding function bodies/handlers and confirms only the existing scoped
installer splice plus owned graft bodies differ.

Build 75's 2,647 Foundation transactions were all local-cache responses and its
post-admission completions were all under 250 ms. This supports prompt **warm
cache task completion after admission** in that run only. It does not test cold
network traffic, cache lookup behind saturated network admission, downstream
pixel/display latency, or universally solved cache performance. Phase 2 remains
the cache-first admission correction; Phase 3 remains residual queue overflow.

### Reproducing the compiled test

Use an existing clone of the public `facebook/hermes` repository checked out at
the revision above. Build the runner with:

```
python3 tools/build_snapshot_runtime.py --source /path/hermes --build /path/hermes-build --cmake /path/cmake --ninja /path/ninja
```

Then, with the corrected Hermes-98 parser dependencies on `PYTHONPATH`:

```
python3 tools/validate_rn_snapshot.py --donor /path/original.hbc --zig /path/zig --hermesc /path/hermesc --runner /path/hermes-build/bin/streamside-snapshot-runner --runtime-source /path/hermes
```

The validator regenerates and checks the payload before execution, rejects
mismatched runtime revision or runner build evidence, and records source/payload
fingerprints, compiler/runner hashes and native acceptance in
`build/snapshot-validation.json`. It writes a privacy-safe host report alongside
that record. The record is local build evidence, not a committed substitute for
rerunning validation. Set `TAS_HERMES_SNAPSHOT_RUNNER`, `TAS_HERMES_SOURCE`,
`TAS_HERMESC`, `TAS_RN_DONOR` and `ZIG` to include this execution test in the full
unittest suite. A missing runtime may skip that expensive unittest, but cannot
bypass the diagnostic build gate.


## Build 77: independent base-value observations

Build 76 stationary Report A reached preparation step 4 on 26 calls, failed
all 26 there, and produced no calculation snapshots. Steps 1–3 all passed;
frame sampling and native delivery were never reached. The library still held
838 committed JS image instances across 168 columns with seven viewable
columns. Foundation recorded 855 local-cache transactions and one network
transaction; this does not establish cache behavior under saturated network
admission. The report does not identify which operation within step 4 failed.

Build 77 separates the previous-range read and nested-list helper into distinct
guards before assembling the numeric array. Each guard records exactly one
aggregate outcome even when the other guard fails:

* Previous range: unavailable (null/undefined), malformed (other type, invalid
  numeric shape, or a throwing property read), or readable. Integer nonnegative
  ordered ranges and RN's empty range 0..-1 are readable. Both properties are
  read once; malformed reads retain neither property value nor exception text.
* Nested-list helper: unavailable (not callable), throws (including property
  retrieval), or succeeds. A captured callable is invoked with the actual list
  receiver; its boolean result is retained only as 0 or 1.
* Base values assembled successfully and snapshot emitted successfully have
  separate counters. Emission success requires the existing native acceptance
  acknowledgement; duplicate suppression and rejected delivery do not count.

Optional range/helper failures leave -1 in the corresponding numeric fields
and do not prevent the remaining snapshot from being generated. Thus a missing
helper cannot conceal the range result or the actual calculated window. The
existing preparation-stage counters still identify failures in later work.
Event 31 adds eight fixed counters (72 bytes), no exception messages, asset
histories, retries, or new capture budget. All original calculations, arguments,
results, query identities, window limits, and transport paths remain unchanged.

Compiled Hermes tests invoke the production graft and native handler with
unavailable values, malformed fields, a throwing range getter, a throwing
helper, both failures together, a correctly bound successful helper, and the
empty-range lifecycle shape. These are host fixtures, not evidence of the
actual on-device helper/range shape or the cause of the expanded RN window.
The fixed 32 accepted-row limit, all preparation failures, restoration, native
rejections, privacy, and report bounds remain tested.

No additional full scrolling test is requested. The next device check, after
compiled validation, is one stationary first opening for ten seconds and one
report. An accepted calculation row must be established on device before
requesting full scrolling. Phase 2 cache admission and Phase 3 queue overflow
remain outside this diagnostic change.

Validation completed: all 96 host tests passed with compiled runtime validation
enabled. The matching Hermes runner delivered 32 snapshots through the
production native handler. Its report recorded independent previous-range and
helper outcome totals of 1/2/38 each, 40 assembled arrays, and 32 accepted
snapshots. The independent HBC verification preserved all 47,322 preexisting
donor functions and regenerated the 127 owned functions successfully. These
counts describe the bounded test fixture, not actual device mounting.


## Build 77 device result and build 78 geometry correction

Build 77 accepted all 16 startup snapshots with no preparation failures,
unsupported calls, original exceptions, or packet refusals. All 16 previous
ranges were readable. The nested-list helper threw on all 16 observations;
its independently guarded -1 field no longer prevented useful snapshots.
This explains the build-76 probe failure without claiming that helper throws
caused the rendering defect.

The stationary range expanded 0..6 -> 0..13 -> 0..20 -> ... -> 0..118,
adding seven columns at every observed adjustment. Capture ended at its
16-row bound. Later aggregate observations showed the range/mask spanning all
168 columns, with 838 committed library image instances live. The viewport
remained 370 points, zoom was 1, pending count 0, batch size 7 and window size
3. All 29 real metric queries per adjustment were valid and agreed with owned
geometry to the existing 0.5-point comparison tolerance. The first content
length was 10080, then 10360; this transient did not explain continuing growth.
Native view attribution remains unknown; these are JS-instance counts.

### Reproduced calculation defect

The owned LibraryGrid supplies fractional-width horizontal columns. At 370
points and six columns per viewport, stride is 370/6. Its old getItemLayout
returned offset = index * stride and length = stride independently. In binary
floating-point arithmetic, column 11's offset + length is
739.9999999999999 while column 12's offset is exactly 740. RN factory 350's
unchanged overlap search (7242) cannot match the overscan endpoint 740 to
either interval. The returned overlap array has no fourth index.

We executed the actual donor factory 350, overlap function 7242 and window
function 7244 in the matching Hermes runtime. With the library's old fractional
geometry, viewport 370, zoom 1, offset 0, batch 7, window 3 and 168 columns,
the result is exactly 0..13, then 0..20, matching the device's startup sequence.
The undefined overscan-end index falls back to itemCount - 1 (167); each new
calculation spends another seven-item batch expanding toward that fallback.
The fixture retains Babel array conversion and feature-flag adapters but does
not reproduce the search or window implementation in JavaScript.

This supplies an evidence-backed explanation: inconsistent floating-point
interval endpoints in owned geometry, rather than a physically oversized
viewport, eager catalog image construction, unstable keys, zero zoom or a
transport capacity problem. The device report rounds sampled coordinates and
therefore does not directly expose the sub-picopoint gap; the exact geometry
and algorithm reproduction bridge that limitation. No assertion relies only
on cumulative loads or the number of queued requests.

### Smallest correction

Build 78 changes only the owned horizontal getItemLayout callback: offset still
uses index * stride, but length is calculated as the next column's offset minus
the current offset. Adjacent interval endpoints now agree exactly. Fractional
visual widths, five rows, adaptive columns, keys, image sources, animations,
filters, recents, insertion, long press, footer navigation, native sections,
initial rendering, batching and window size remain unchanged. The original RN
algorithm and all donor function bodies are unchanged. There is no artificial
window clamp, added prefetch, capacity/concurrency increase, transport change,
cache-admission change, or queue-overflow redesign.

The compiled validation gate additionally executes the unchanged donor RN
window algorithm with the production graft's actual getItemLayout callback.
It covers 12 viewport widths (320–1024), six catalog sizes (1–5000 emotes), both
collapse-window feature-flag branches, and 11 stationary/gradual/rapid/backward
positions: 1584 window calculations. It checks contiguous geometry, bounded
ranges, inclusion of visible columns, five-row mapping, stable column/tile
keys on rerender/reopen, and preserved image elements/sources for visible
logical items. Existing library fixtures retain provider/scope changes,
channel changes, native callbacks, search, details, disable fallback and
consumer cleanup coverage. Host React facade tests do not establish actual
Fabric recycling, physical display, animations or device cancellation.
The snapshot pipeline still must produce 32 native-accepted host packets.

### Transport evidence and next device check

Build 77 was mixed traffic: 610 Foundation network transactions and 41 cache
transactions, with 651 measured completions. Queue waits were 14 <=250ms,
26 <=1s, 617 <=5s; current/peak queued flights were 140 and oldest queued age
4.4 seconds. Library source-to-onLoad had 463 callbacks above five seconds.
Those queues are flights, not 140 simultaneous image views. Completion timing
still mixes cache/network and excludes queue and decode; source-to-onLoad does
not prove pixel display. This does not establish cache correctness/performance
under eight occupied network slots. Phase 2 and Phase 3 remain separate.

Next device validation: restart Twitch, open the same large-catalog library,
stay stationary for ten seconds and capture A. Then scroll horizontally once,
close/reopen, stay stationary ten seconds and capture B. Verify that the first
range stops near the viewport/overscan window instead of continuing +7 toward
168, that visible images render, and that dismissal releases old consumers.
No further general tracing system or full-catalog scrolling pass is requested.

## Build 78 device confirmation and regression baseline

The supplied reports A and B confirm the geometry correction on Twitch 31.5.
They cover a stationary first opening, scrolling, dismissal and stationary
reopening of a large provider catalog. No further calculation tracing or
diagnostic IPA is needed to preserve this result.

| Observation | Build 77 | Build 78 A / B |
| --- | --- | --- |
| Catalog columns / viewport width | 168 / 370 pt | 168 / 370 pt |
| Stationary first opening | 0..6 -> 0..13 -> 0..20, continued growth | 0..6 -> 0..11 -> 0..11 |
| Stationary library JS live instances | 838 | 60 |
| Reopening | Full catalog in prior build 75 reports | 0..6 -> 0..11 -> 0..11; 60 live |
| Scroll calculated range / render mask peak | Not exercised in build 77 report | 19 / 26 columns; 130 JS instances |

Report B is cumulative across three openings, not an independent second launch.
Its library totals are 370 mounts, 310 unmounts, 60 currently live, peak 130,
370 load starts and 370 successful onLoad callbacks, with no errors or unmatched
callbacks. The scroll stage had 190 mounts and 120 unmounts. Two close stages
account for 190 further library unmounts and 48 recent-image unmounts, matching
the outgoing 130- and 60-instance library windows and two 24-instance recents
sets. This supports cleanup across the exercised dismissals; it does not
establish cancellation of an active network request during dismissal because
the reports have no protocol cancellation observations. The range and render
mask have different sizes; a mask can include retained initial cells. Neither
is synonymous with cumulative loads or unique assets. Native attribution still
remains unknown; the scoped counts are JS instances.

All 370 library source-to-onLoad callbacks completed within five seconds:
140 <=250 ms, 122 <=1 s, 108 <=5 s. This measures source assignment to load
callback, not pixel display. Report A had 74 network / 6 local-cache Foundation
transactions; cumulative B had 259 / 108. First-opening queue waits still
included 56 in the 1–5 second bucket. These reports do not establish a cache
delivery path independent of saturated network admission. Phases 2 and 3 remain
unchanged and unimplemented by this regression-only follow-up.

### Maintained checks

`tests/fixtures/window_baseline.json` names the confirmed baseline as
`build78-fractional-columns-v1`. It retains the observed 370-point, 838-emote
first/idle/reopen result 0..11 and a broader 12-width, six-catalog matrix up to
5000 emotes. The exact 0..11 assertion is specific to that donor/configuration;
a deliberate future RN change may require reviewed expectations. The geometry
and proportional-window invariants must remain satisfied.

* Ordinary CI runs `test_fractional_columns_and_identity_on_first_open_and_fresh_reopen`.
  It executes owned production JS through the React host facade, checking exact
  adjacent endpoints, fractional widths, five-row item mapping and stable
  column/tile keys through rerender and a fresh grid remount. It requires no
  redistributed Twitch bundle. It does not simulate RN window calculations.
* The compiled Hermes fixture executes the production graft and unchanged donor
  overlap/window bytecode. It retains the old-geometry runaway as a negative
  control. Each matrix case now runs 20 stationary calculations after first
  opening and 20 after an actual host grid-state reset and new layout event,
  under both feature-flag settings. It also retains gradual/rapid/backward
  scroll calculations, bounded ranges and visible-image element/source checks.
  The total is 7344 successful window calculations. Repeated idle calculations
  must stay fixed rather than spending another batch toward the catalog end.
* `check_gate` explicitly requires the named baseline, complete window scenario
  count, successful window validation, pinned donor/runtime and current input
  hashes alongside the snapshot result. Missing, failed, partial, wrong-donor
  and stale records are tested and block diagnostic packaging.
* `make test-rn-virtualization` is the required compiled check for library changes
  and Twitch ports. Unlike the environment-dependent unittest, it fails when
  toolchain/donor inputs are absent. Public CI still lacks the donor and does
  not claim compiled Hermes coverage. A new Twitch bundle cannot inherit the
  old record: review the donor hash, bindings and feature adapters, and execute
  the actual new donor algorithm before approving the port.

The host facade resets owned grid state and exercises logical reopening but
does not model Fabric recycling or native scroll event scheduling. Device A/B
provide the actual first/open/scroll/reopen observations for this baseline;
they do not certify untested widths, filters, channels or every future donor.
No shipping JS, payload, transport, concurrency, cache policy or build number
changes are part of this follow-up.

Validation: all 98 host tests passed with matching Hermes execution enabled;
the required compiled target passed 7344 window calculations and 32 accepted
snapshots. A temporary negative-control copy with the old constant-length
geometry failed the ordinary CI endpoint test. The compiled target also
rejected absent toolchain/donor inputs. No production file was mutated for
either negative control, and no new on-device behavior is claimed beyond A/B.
