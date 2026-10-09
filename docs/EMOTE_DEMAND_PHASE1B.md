# RN library demand — phase 1B investigation

Baseline: diagnostic build 73, commit
`58b82e3124b1361cff369cc952ef66cf297a1638` (build-72 rendering and transport).
The implementation is diagnostic build 74. Its four-report device pass has now
been analyzed. A full-catalog startup range is established, but the update and
cell metrics that produce it are not. No virtualization correction is yet
justified; Phase 1B remains open. The remaining evidence needed is described
below, rather than asking for the original ten-report matrix again.
Build 75 adds the narrowly scoped boundary trace documented in
[EMOTE_DEMAND_PHASE1B_CALCULATION.md](EMOTE_DEMAND_PHASE1B_CALCULATION.md);
its two-report test replaces further unchanged-build-74 captures.
Cache admission, flight identity, cancellation decisions, the 512-flight
capacity, eight active slots and six background slots remain unchanged.

## Established device distribution

The supplied build-73 PDF contains six cumulative snapshots in one process.
These are committed JS diagnostic image instances, not native view counts.

| Capture | Activity | Cumulative mounts | Cumulative unmounts | Live | Launch peak | Cumulative load starts |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A | Library closed baseline | 0 | 0 | 0 | 0 | 0 |
| B | First opening, stationary | 950 | 0 | 950 | 950 | 950 |
| C | Rapid horizontal scrolling, then waiting | 2,090 | 1,960 | 130 | 950 | 2,090 |
| D | Reopening **and scrolling back**, not an isolated reopen | 3,630 | 3,500 | 130 | 950 | 3,630 |
| E | Library dismissed; composer test | 3,630 | 3,630 | 0 | 950 | 3,630 |
| F | Suggestions test | 3,630 | 3,630 | 0 | 950 | 3,630 |

B demonstrates 950 simultaneous JS image instances because no library instance
had unmounted. It is not an inference from 950 load starts. It does **not**
establish 950 distinct image assets, native Fabric views or visible images.
The catalog contained 950 channel 7TV entries; URL deduplication was not counted
specifically for those JS mounts. C adds 1,140 mounts but has only 130 live
instances. D adds 1,540 mounts and 1,540 unmounts; it cannot independently isolate
reopening from backward scrolling. E establishes JS release on dismissal.

At B the measured outer viewport was 370 × 625, inner horizontal viewport
370 × 260, content 11,716 × 260, and maximum viewability seven columns. Geometry
maxima and counts are separate observations, not synchronized frames. They
contradict a persistently catalog-wide layout viewport. B also has 3,615 commits,
950 source-value changes and 2,665 same-source commits, with 950 load starts.
This does not support an image reload on every rerender as the initial cause.
Recents have 20 live instances separately; they cannot explain the library peak.

| Capture | Global active transfers | Current/peak queued flights | Current/peak consumers | Cumulative queued cancellations | Cumulative budget refusals |
| --- | ---: | ---: | ---: | ---: | ---: |
| B | 6 | 128 / 128 | 134 / 134 | 0 | 0 |
| C | 6 | 51 / 506 | 57 / 514 | 975 | 125 |
| D | 0 | 0 / 506 | 0 / 514 | 1,269 | 264 |

Those transport values cover all provider consumers, not just library tiles.
The report's 512 registry peak is neither a mount count nor a unique asset count.
All six captures report zero header mismatches and zero probe-table evictions.
Foundation's local-cache transaction durations are all at most 250 ms, but the
aggregate snapshots cannot pair an individual cached transaction with its queue
wait. No cache-first change is included here.

## Build-74 four-report device results

Source: the supplied 79-page `Build 74 testing logs.pdf`, reports A-D. These
correspond to the reduced baseline / first opening / scrolling / close and
stationary reopen pass. Reports are cumulative within one process. C also
records backward movement; its forward and backward stage totals must not be
treated as separate captures. D has two openings, and the close-stage cleanup
accounts for all 107 library instances live at C.

| Capture | Cumulative JS mounts | Cumulative unmounts | Live | Launch peak | Load starts | Successful loads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A: closed baseline | 0 | 0 | 0 | 0 | 0 | 0 |
| B: first stationary opening | 837 | 0 | 837 | 837 | 837 | 595 |
| C: scrolling, including backward movement | 2,426 | 2,319 | 107 | 837 | 2,426 | 2,426 |
| D: close and reopen | 2,501 | 2,426 | 75 | 837 | 2,501 | 2,501 |

First-open stage observations:

- 837 mounts, zero unmounts, 837 peak/live instances before stabilization.
  There are 834 bounded unique asset fingerprints and three concurrent
  duplicate-asset mounts, with zero table evictions or probe refusals.
- RN reports 168 cells around the viewport and 168 non-spacer mask columns
  against a 168-column catalog. Internal viewport length is at most 370 points,
  content length 10,360 points, and external viewability at most seven columns.
  Maxima are separate observations; the existing stage summary does not retain
  synchronized tuples or the sequence of window adjustments.
- Actual initial/batch counts are seven columns; window size is three. In the
  13 startup samples there are no zero/missing zoom, same-orientation nesting,
  disabled-virtualization, pending-update, or nonzero-offset observations.
  Non-unit/non-finite zoom and cell-metric validity are not classified.
- The settle probe reports no timeout. Idle adds zero mounts and zero unmounts,
  so all 837 instances remain mounted after the initial telemetry stabilizes.
  Only 595 have completed their image callback at B.
- There are 4,016 committed renders but only 837 source-value assignments and
  837 load starts. The 3,179 same-source commits are not evidence of a download
  per render. Recents are a separate 22 live instances; suggestions/info are zero.

**Established defect boundary:** the owned provider row's horizontal FlatList
reaches a full-catalog `cellsAroundViewport` range on first opening. This is
not merely a focused/initial region added to a small viewport range: the range
itself expands, as does the mask. The small measured viewport and configured
seven-column initial batch do not bound the actual startup image population.
The data does not support blaming eager recents, disabled virtualization,
persistently excessive layout width, source-object rerenders or multiple full
library instances for the startup count.

**Still not established:** which update or metric makes RN choose that range.
Stage maxima cannot show whether the viewport/range/zoom/cell metrics were
valid together at the expanding update. The sample interval can miss a
transient invalid input. Donor inspection confirms the constructor initializes
zoom to one, FlatList forwards `getItemLayout`, and the viewport adjustment
uses `computeWindowedRenderLimits` (7244), except for missing dimensions,
pending updates or disabled virtualization. Function 40828 schedules its
state updater 45709; the aggregate report does not record that updater's input
and output. A zero-zoom clamp, smaller window, forced key reset or custom
virtualizer is therefore still a guess, and none is applied.

After scrolling, C has 107 live instances, despite 1,589 additional mounts.
Forward/back stage remounts total 1,586; these are asset reappearances after
their observed library live count reached zero, not proof of unstable React
keys. The 837 stage peaks can inherit the initial live population and are not
proof that every later scroll mounted the catalog again. Range/mask maxima
also remain aggregate, not a time series. Close releases 107 library and 22
recent instances. The new opening reports a seven-column range/mask in three
startup samples and 70 mounts before settling; five further mounts are
classified under scroll. D ends with 75 live and all 75 new load callbacks
completed. Do not equate its seven-column sampled mask with all later live
instances, or assume that the five stage-classified mounts reflect a deliberate
user swipe: initialization can generate native scroll events.

| Capture | Shared task starts / completed | Queue waits >5 seconds | Current / peak queue | Registry refusals | Foundation network / local-cache transactions |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 0 / 0 | 0 | 0 / 0 | 0 | 0 / 0 |
| B | 617 / 611 | 109 | 165 / 165 | 0 | 482 / 129 |
| C | 1,628 / 1,628 | 345 | 0 / 165 | 0 | 688 / 940 |
| D | 1,722 / 1,722 | 345 | 0 / 165 | 0 | 688 / 1,034 |

All captures have zero queued cancellations, active detaches, header mismatches
and transport errors. These are global provider transport counts, not library
consumer counts. Foundation's local-cache fetches all fall within 250 ms;
they start only once a shared transfer slot admits the task. At B the library's
source-to-onLoad buckets are 2 / 3 / 140 / 450, and at C they are
1,591 / 3 / 140 / 692. These include queueing and downstream work; they are not
network-only durations or isolated decode/display latency. The cache scheduling
issue remains Phase 2. This pass demonstrates slow initial completion even
without any registry refusal; raising capacity would not correct that cause.

Native library attribution remains zero in all reports. The conclusions above
use reliable JS-instance and RN-state observations, not the unknown Fabric pool.
The logs cannot prove pixel visibility or enumerate every hidden native section.

### Remaining targeted boundary evidence

Do not repeat the ten-stage test to fill fields it cannot expose. The missing
discriminator is a bounded observation of the **expanding window calculation**:
previous and proposed range; synchronized visible length, zero/nonzero offset,
finite/unit zoom, pending count and catalog length; and a small fixed sample of
cell length/offset validity compared with the owned `getItemLayout` geometry.
It must distinguish a stale retained range from incorrect overlap inputs and
stay scoped to the owned provider list. A read-only probe must not replace
RN methods globally, log item identities, or change window calculations.

If such instrumentation can be implemented safely, the device pass can be just
first stationary opening and stationary reopening, with one scroll between
them. Otherwise retain these findings and defer the correction. No additional
device report is requested against unchanged build 74: its current aggregates
cannot resolve the missing inputs. No code, payload, binary, cache, scheduler,
capacity or concurrency changes accompany this analysis. The previously
validated 92-test implementation remains unchanged; documentation-only updates
do not constitute new device or virtualization test evidence.

## Exact boundary inspected

`src/rn/ProviderEmoteStrip.js` installs through composer factory 4869 and the
verified `EmotePickerTray` leaf 4174 (factory 4178, donor function 20057). JSX
module 245 routes only `emote-grid-list` and `emote-nav-tablist` through the
library context. Native sections, callbacks, footer navigation and the input
remain Twitch implementations.

Hierarchy:

1. Twitch tray / owned `LibrarySession`, keyed by channel and picker session.
2. Owned `LibraryGrid` adapting Twitch's **vertical** `SectionList`.
3. One provider section, placed after native recents and before channel subs.
   Its one 260-point row contains a **horizontal** `FlatList`.
4. Each column has at most five 52-point tiles, each containing one image.
   Column width = measured outer width / clamp(floor(width / 60), 3, 12).
   Catalog index `i` maps to column floor(i / 5), row i % 5.
5. Provider recents are a separate eager horizontal ScrollView capped at 40,
   frozen until a new library opening. Suggestions are separate and capped at 64.

The owned row materializes column **descriptors**, not image elements, for the
catalog. Only `FlatList.renderItem` creates each column's five image children.
At 370 points there are six adaptive columns across the viewport, with a
partially visible boundary column possible. Initial and batch counts are seven
columns; window size is three viewport lengths. `getItemLayout` supplies exact
column offsets. Outer provider row height does not grow with catalog size.

The exact donor's FlatList render function 25811 forwards these props to
VirtualizedList. Its constructor (25815), adjustment (25830), render mask
creation (25861), initial region (25862), render (25837), content callback
(40821), layout callback (40817), scroll callback (40823), and non-viewport
focused regions (40830) were inspected. The window algorithm is function 7244
exported by factory 350; offset overlap search is 7242.

Important distinctions:

- RN computes its window from `_scrollMetrics.visibleLength`, offset and zoom,
  plus list metrics. The existing `onLayout` maxima do not prove these internal
  startup metrics were correct at each window calculation.
- The render mask adds the retained initial region and any focus region to the
  ordinary viewport window. A 130-image later window is therefore not proof
  of excess overscan by itself: it includes up to 26 five-image columns and may
  include the seven retained initial columns.
- Horizontal nesting is determined by RN context at runtime. The owned inner
  and outer orientations differ, but the old report never read the runtime
  nesting predicate, disable flag, pending updates or mask.
- Column keys are section title plus starting index; tile keys are stable
  provider IDs. Same-catalog rerenders retain these identities. A provider/scope
  key change intentionally resets the horizontal list. Filtering can regroup
  tiles, so those transitions can legitimately remount them.
- The outer list may retain the provider row while it is offscreen. The current
  report does not establish the precise lifetime of all hidden native sections.

**Underlying cause not yet established:** build 74 demonstrates an expanded
viewport range and mask, narrowing the earlier alternatives. It does not
capture the inputs and update that create them. Static configuration is
insufficient to choose a correction. Donor 40823 accepts zero zoom scale and
7244 uses it in overlap calculations, but build 74 reports no zero zoom in
sampled startup states. This hypothesis is not established by the device data.
No guessed clamp, custom virtualizer, key reset or tile hiding is applied.

## Build-74 observations and limits

The diagnostic-only `LibraryColumnsTrace` preserves the underlying FlatList,
its geometry, source rendering, keys and callbacks. It reads the verified
FlatList `_listRef` and bounded VirtualizedList state at layout, content,
viewability and scroll boundaries. No RN method or render mask is modified.

It reports stage-specific aggregate image mounts, unmounts, live peaks, load
attempts/results, bounded unique assets, asset remounts and concurrent duplicate
assets. Asset remount means a previously mounted URI fingerprint with no
currently observed library instance of that asset. It is not proof of the same
React instance being recreated. Source changes also contribute unique assets.
Evictions and fingerprint collisions qualify these counts; no history grows
with catalog size. Late signals from an older session are counted and excluded
from current-session image stage counters.

Stage definitions:

| Stage | Definition |
| --- | --- |
| open | First library session, before the first stable internal viewport sample |
| reopen | Subsequent session's initial interval, including channel/session replacements |
| idle | Two matching, positive internal viewport/content samples 250 ms apart after activity stops |
| scroll | Horizontal offset advances; absolute offsets are not retained or reported |
| scroll-back | Horizontal offset retreats |
| filter/scope | A provider or scope selection starts a new window transition |
| close | Library session cleanup; also the initial closed-app baseline |

Stages aggregate repeated occurrences. Reopen is anonymous session replacement,
not proof that the channel remained the same. The sampler has one cancellable
timer, at most 20 samples over five seconds per settling interval. Startup that
never stabilizes is explicitly counted; it stays in its initial stage. Idle
means stable list telemetry, not successful decode/display or completed loads.

Each stage also records maximum actual cells-around-viewport span, non-spacer
render-mask columns, catalog columns, internal visible/content lengths, configured
initial/window/batch limits, pending scroll updates, nonzero-offset observations,
zero/missing zoom, same-orientation nesting and virtualization-disabled flags.
At most 16 mask regions are examined; unsupported refs/regions count refusals.
Short-lived states between callbacks/samples can still be missed; committed
image peaks independently capture mounts, including before stabilization.

Transport hooks only observe occupancy after existing admission, completion,
scheduling and cancellation transitions. Stage active/queued/consumer peaks and
cancellation totals are **temporal all-provider** observations, not caller or
per-asset attribution. Cancellation means queued last-consumer removal plus
active last-consumer detachment; it does not claim network task cancellation.
Lock order is transport lock → demand lock; the demand probe never calls back
into transport. Cache hit classification/timing remains Foundation metrics.

Native attribution stays unresolved: all scoped Fabric counts in build 73 were
zero despite installed hooks. No intrusive or guessed native attribution hook
is added. JS attribution is the reliable library instance evidence.

Reports contain only aggregate numbers. No chat, channel identity, emote names,
URLs, headers, tokens, image bytes, fingerprints, pointers or session sequence
values are reported. Tables remain fixed at 2,048 assets/requests and 4,096
native observations, below 512 KiB combined, plus seven fixed stage summaries.

## Original full device matrix (reference; superseded for this tracing pass)

The user completed the reduced four-report pass above. This original matrix
is retained for eventual regression coverage, not a request for ten more logs.

Use build 74 and restart Twitch once before testing; do not restart between
steps. Clearing the text log does not clear these cumulative counters. Use a
quiet channel with at least 900 7TV entries and record each labeled report.

1. **A — closed baseline:** remain in chat, library closed, ten seconds.
2. **B — initial stationary open:** open the library, leave it untouched for
   ten seconds. This is the decisive startup mask/zoom/viewport capture.
3. **C — gradual forward:** move one horizontal screen at a time, pause two
   seconds between three moves; stop ten seconds and capture.
4. **D — rapid forward:** swipe five screens rapidly, stop ten seconds, capture;
   note whether all visible tiles eventually fill.
5. **E — scroll back:** return to the first screen, wait ten seconds, capture.
6. **F — idle:** leave it untouched another ten seconds, capture. Mount/load
   deltas should distinguish stable idle from repeated demand.
7. **G — filter/scope:** select 7TV, BTTV, FFZ, All, Global, Channel, allowing
   two seconds each; capture. Exercise search if available, insertion, long
   press details, native section navigation and whole-emote backspace.
8. **H — closed:** dismiss the library, wait five seconds, capture. Library and
   recents JS live should reach zero; inspect current consumers separately.
9. **I — clean reopen:** reopen the same channel, **do not scroll**, wait ten
   seconds, capture. This separates reopening from backward scrolling.
10. **J — channel replacement:** dismiss, switch channel, reopen; wait ten
    seconds, capture. Report stage deltas and note the action, without sharing
    channel identities. Separately test one chat and one composer emote.

If B shows ~190 mask columns with a small actual viewport, examine zoom/nesting/
disable/pending counters before choosing a correction. If the mask stays small
while mounts reach 950, investigate another rendering path or missed transient
states rather than imposing an arbitrary smaller window. Nonzero refusals or
settle timeouts limit interpretation. Do not infer mount bounds from transport
occupancy or cumulative loads.

## Validation boundary

Host tests cover exact owned diagnostic callbacks, original handler forwarding,
stable tile type/key/source across rerenders, geometry for 1/35/950/5,000 entries
at 180/370/768-point widths, stage transitions, large internal mask reporting,
missing refs, bounded timer exhaustion, dismissal cleanup and reopening.
Production C fixtures cover 950 simultaneous JS observations, asset uniqueness
versus duplicate mounts, backward remounts, reopen/late-session exclusion,
temporal transport summaries, privacy and fixed memory budgets. Shared transport
lifecycle tests run with diagnostics both enabled and disabled.

These fixtures do not execute the real Fabric/Yoga virtualizer, establish actual
device render-mask distributions, prove pixel visibility or verify image
recovery under congestion. The diagnostic build deliberately does not claim a
bounded device mount window yet. No cache-first or overflow/retry tests are
claimed. Device evidence must select the smallest rendering correction before
Phase 1B can be declared complete.

Build-74 checks passed: 92 host tests; exact Hermes-98 graft verification with
all 47,322 donor functions preserved and 117 owned strip functions (22,896
payload bytes); iOS diagnostic framework build and unsigned IPA packaging.
Framework SHA-256:
`a92970641cc158e859e7495aadf1b9286090e0b9ea653aee673568ed8e8652b1`.
