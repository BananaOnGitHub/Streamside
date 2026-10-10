# Provider image demand — phase 1

> Archived investigation: `archive/rn-image-demand`, completed through build 87
> and fast-forwarded into `compat/twitch-31.5`. The baseline and procedures below
> describe build 73. Subsequent work fixed fractional-column demand and added
> cache-first delivery and bounded overflow recovery. See the
> [branch closure](DIAGNOSTIC_BRANCH_ARCHIVE.md#rn-image-demand-builds-73-87)
> and [current transport notes](EMOTE_IMAGE_TRANSPORT.md#builds-79-83-cache-first-delivery-and-overflow-recovery).

Baseline: `compat/twitch-31.5`, build 72, commit
`645d34f2a3617f73072fa7d7d635af5ffa28b2f9`.
Diagnostic build: 73, `IMAGE_DEMAND_DIAGNOSTIC=1`, `EMOTE_DIAGNOSTIC=0`.

This change observes demand. It does not implement the cache-first path, change
virtualization, add retries, increase the 512-flight registry or eight active
slots, or introduce another downloader. Phases 2–4 remain outstanding.

## Findings and remaining uncertainty

There is a confirmed cache scheduling problem in the build-72 source: eligible
image requests enter the shared-flight registry and wait for an active slot
before Foundation creates the task that can consult its HTTP cache. A fresh
cached response can therefore wait behind uncached work. Existing task-completion
latencies include HTTP-cache responses and must not be called network download
times.

There are also plausible sources of excessive demand, but the existing reports
cannot rank them. Build 72 reported 2,729 queued cancellations, 756 budget
refusals and 213 queue waits over five seconds. These counts are repeated
lifecycle events, not counts of mounted views or unique emotes. In particular,
512 occupied flight entries do not establish 512 mounted images or 512 distinct
assets.

Static inspection establishes the following hierarchy and configuration:

| Surface | Implementation | Demand implications |
| --- | --- | --- |
| Library outer list | Twitch vertical `SectionList`, donor function 20057; initial and batch counts 8, window size 3, batching period 50 ms, clipping disabled | Existing native sections and provider section share this list. Initial retained cells and outer offscreen sections need device observation. |
| Provider section | One 260-point row containing a horizontal `FlatList`; columns contain five 52-point tiles | Each mounted column can mount five images. Window size 3 refers to viewport lengths, not three columns. |
| Provider sizing | Starts at width 360; columns are `floor(width / 60)`, clamped to 3–12; cell width is width divided by columns | At width 360, initial and batch counts are seven columns, up to 35 image children. This is a configured initial batch, not a measured device peak. |
| Recent provider emotes | Horizontal `ScrollView`, at most 40 tiles; snapshot taken on library opening | Eager children; selections do not immediately refresh the open snapshot. |
| Suggestions | Horizontal `ScrollView`, at most 64 entries | Eager children, independent of the provider library's virtualization. |
| Chat | `EmotePart`, donor function 19127, through Twitch's `CoreImage` with string `src` and `chat-emote-` test-ID prefix | Preserve the original image component; observe only the verified JSX boundary. |
| Composer | Native Swift emote input using synthetic URL redirects and its own GIF preview handling | Does not use the library's React image wrapper; transport attribution uses the native URL-completion boundary. |

The inner list has no explicit width in its style. Yoga/Fabric must establish
the actual viewport width; static code cannot establish whether that width is
bounded correctly on the device. The new geometry counters distinguish inner
layout width from content width and viewable-column count. They do not change
layout, list configuration, or React state.

Provider filters change the inner list key and can remount images. Tile renders
create fresh source objects with stable URI values and stable keys. A new source
object is not itself evidence that RN restarted a request: committed source-value
changes, same-source commits, load starts, and protocol requests are now counted
separately. Eager recents/suggestions and initially retained outer cells may add
demand outside the visible provider columns.

## Request lifecycle in build 72

1. The owned RN graft installs through verified writable exports and scoped JSX
   adapters. The composer factory is 4869; library leaf 4174; the JSX runtime is
   module 245. The provider section preserves the native library list and footer.
2. Mounted RN image components assign provider CDN sources. Chat and native
   input may instead construct synthetic Twitch emote URLs, which existing hooks
   map to provider images. Native input also maintains a separate bounded GIF
   body cache (128 objects / 8 MiB); it is not Foundation's HTTP cache or RN's
   decoded-image cache.
3. Provider requests reach `NSURLProtocol`. Public, bodyless GET requests without
   Authorization, Cookie or Range headers are eligible for shared transport.
   Existing build-72 inner request policy normalization remains unchanged.
4. Coalescing uses the full URL and equality of all HTTP header fields. It does
   not canonicalize variants. A flight holds at most 64 independently cancellable
   consumers; differing headers or full consumer groups can create another
   flight for the same URL. The diagnostic signatures do not replace this key.
5. Admission is bounded to 512 entries. Scheduling allows eight active tasks,
   with at most six background/direct-image tasks. Recognized native redirects
   retain foreground priority; this is not viewport-aware library prioritization.
   Within a priority class, generation order is preserved.
6. Only an admitted active flight creates/resumes a Foundation task. The dedicated
   image session has a 32 MiB memory / 128 MiB disk `NSURLCache`, request/resource
   timeouts of 15/30 seconds, and a delegate queue bounded to four operations.
   HLS uses a separate session. Foundation performs cache freshness/validation
   handling after task creation, behind the flight scheduler.
7. Removing the last queued consumer removes the entry without starting a task.
   Removing the last active consumer leaves a detached task running toward
   completion/cache fill, within the existing session timeouts. Matching later
   consumers can rejoin it. Detached tasks still consume active capacity.
8. Completion removes the flight before fan-out and reschedules queued work.
   Consumer stop flags and flight generation guards prevent stopped consumers
   and reused entries from receiving stale delivery. Registry refusal delivers
   an error; there is no explicit visible-image recovery mechanism in this path.

The unresolved alternatives are oversized mounted windows, eager retained
sections, repeated request starts on same-URI commits, request variants that
split flights, and detached work consuming slots. The instrumentation below
separates these possibilities without choosing a phase-3 correction yet.

## Added observations and interpretation

| Observation | Meaning and limits |
| --- | --- |
| JS mount/unmount/live/peak | Committed diagnostic image-wrapper instances, partitioned into library, recents, suggestions, info and chat. Not attempted renders, native view counts, or visible pixels. |
| Commits / source changes / same source | URI-value comparisons across committed renders. Does not equate source-object identity with a fetch restart. |
| Load starts / loads / errors | Original image callbacks are chained. Old-source callbacks remain forwarded; unmatched callbacks are separately counted. Some Twitch components may not forward these events. |
| Source-to-onLoad buckets | First matching callback after the committed source observation. Includes scheduling, cache/network work and downstream processing; not an isolated decode or pixel-display measurement. |
| Native live/window/peak | Bounded observations of `RCTImageComponentView`, with window, layout, recycle and deallocation hooks. Window membership is not viewport visibility. Views created before hook installation can be absent until observed. |
| Library geometry | Separate outer layout, inner layout, content-size maxima, and viewable-column maximum, plus callback counts. Maxima may come from different moments; no scroll coordinates are retained. |
| Asset / URL+header first/repeat | Bounded in-memory fingerprints distinguish repeated asset observations from request variants. Evictions begin new observation intervals; collisions remain possible. These are not exact launch-wide unique counts. |
| Flight occupancy / ages | Current and peak occupied entries, queued entries and consumer count; current detached count; oldest queue/detached ages. Entries and consumers are different units. |
| Same URL comparisons / header mismatch / full group | Observations at existing coalescing decisions. Comparison counts can exceed request counts because a request scans multiple entries. |
| Detached completion / rejoin delay | Time after the last consumer detaches. Shows whether retained work completes or becomes useful again; no lifetime change is made. |
| Foundation fetch classification | Real session metrics distinguish unknown, network, push and local-cache transactions. At most 16 transactions per callback; empty and truncated metrics are counted. Multiple transactions may belong to one task. |
| Local-cache timing | `fetchStartDate` to `responseEndDate` for Foundation local-cache transactions; excludes registry queue wait and downstream decode/display. Missing timestamps do not enter timing buckets. |

URL-object markers attribute recognized native redirects and the native input
URL-completion boundary when the marker survives. The redirect category is not
exclusively chat. Unmarked protocol requests correlate against historical
JS asset-scope masks; multiple/unknown scopes are reported explicitly. This
correlation is not proof of the initiating caller. The observed chat JSX boundary
does not guarantee coverage of every image path or already-mounted image.

Diagnostics are independently compiled behind `IMAGE_DEMAND_DIAGNOSTIC`. They
add no network requests, cache lookups, retry loops, prefetching or polling.
Fixed tables hold 2,048 asset fingerprints, 2,048 request signatures and 4,096
native observations; their combined storage is below 512 KiB. Refusals and
evictions qualify the counts. URL/header strings are inspected transiently with
bounded budgets (2,048-byte strings, at most 32 header fields and 16 KiB total
header text); fingerprints and native pointers stay in RAM. Reports/logs contain
no chat text, channel identities, emote names, full URLs, headers, tokens, image
data, fingerprints or object addresses. Diagnostic overhead means this build is
for tracing, not a clean production performance benchmark.

## Targeted device test

Actual device mount counts and the cause of the oversized demand cannot be
established from static analysis or the host mocks. Install the surviving build-73
diagnostic IPA and restart Twitch before the test. Clearing the text log does
not reset launch counters. Use report deltas between steps:

1. Stay in chat with the library closed for ten seconds; capture a baseline.
2. Open the provider library in a quiet channel with several hundred emotes.
   Leave it stationary for ten seconds; capture a report.
3. Scroll horizontally rapidly, then stop on a partially blank region for ten
   seconds. Capture a report and note whether the visible blanks eventually fill.
4. Close the library for five seconds, then reopen with the same filters. Wait
   ten seconds and capture a report. Compare cache classifications, queue wait,
   mounts and source changes with the first opening.
5. Separately exercise composer preview and suggestions, dismiss them, and
   capture deltas; optionally repeat with a populated recent-emote strip.

Steps 1–4 are the smallest useful initial trace. A large inner width, high
stationary JS/native peak and many columns would support a viewport/window
problem. Stable mounts plus rising same-source commits/load starts/protocol
repeats would support restart churn. Small mounted counts with many flight
entries/header splits would point farther down the lifecycle. Substantial
detached occupancy/age would implicate retained active work. Cache-classified
tasks preceded by long queue waits would confirm delayed cached reuse on device.
Zero counters can mean a missing hook or callback path; inspect installation
status and refusal counts before interpreting them as absence of demand.

## Validation and recovery provenance

Recovery validation passed:

- 91 host tests, including production shared-flight lifecycle code with the
  demand flag both disabled and enabled, bounded probe fixtures, original
  callback preservation, bridge ABI registration, and owned JS lifecycle tests.
- Exact Twitch 31.5 / Hermes 98 graft verification: all 47,322 donor functions
  preserved; 101 owned functions / 19,768-byte strip payload; independent
  disassembly and original constants/handlers/debug checks passed.
- iOS diagnostic framework compilation and unsigned-IPA packaging verification.
- Rebuilt framework **byte-for-byte identical** to the surviving build-73
  framework: 500,464 bytes, SHA-256
  `ee1a18931bd6faa12f4e4e44e767ac19b94f8c9d84f9c5b431825e5aa1de00b5`.

Host fixtures do not exercise real Foundation freshness/revalidation, Yoga,
Fabric scrolling, device mount counts or actual decode/display timing. No
phase-4 cache-first tests are claimed; that implementation does not exist yet.

The lost commit was `ef7cd0977482d6ffe50d97968ce54161f725a10d`. Before
reconstruction, the entire conversation workspace was recursively inventoried:

- One Git store (`streamside/.git`); no alternate object stores, Git pointer
  files, linked-worktree metadata or `commondir`. `git worktree list` listed only
  the original checkout.
- All reflogs inspected; no lost commit or diagnostic-worktree creation entry.
  `git fsck --full --no-reflogs --unreachable` completed without unreachable
  objects. `git cat-file` could not resolve the lost object.
- Loose objects and both pack indexes checked. Both packs verified successfully;
  neither contained the object. Before recovery, Git reported 67 loose objects,
  1,210 packed objects in two packs, and no garbage; these counts are not a set
  of distinct objects because loose/packed copies can overlap.
- 37 retained build/object artifacts inventoried, including older build
  55/56/59/70/71 IPAs, the donor IPA, framework and dylib outputs. Workspace text
  and build/object caches were searched for the lost SHA and demand-probe/report
  markers. Toolchain/donor/React trees, the original donor dump and compressed
  IPA contents were excluded from that text-marker search; the surviving
  build-73 IPA was extracted and inspected separately.
- No `EMOTE_DEMAND_PHASE1.md`, Git bundle, patch or diff backup was found in the
  workspace. An exact saved-file search did not find the report. A separate
  personal-context search failed and is not treated as evidence of absence.
  The remote commit lookup returned no such commit.

The saved build-73 IPA survived. Its embedded Twitch bundle matches the original
donor bundle; the framework contains the demand bridge, counters and metrics
delegate. Recorded source changes were restored on the exact build-72 baseline,
the owned Hermes payload was regenerated, and the resulting compiled production
implementation matched that reference byte for byte. Tests and this report were
restored from the recorded findings; the original document bytes and Git commit
metadata were not recovered. The replacement commit therefore has a new identity.

Reference IPA SHA-256:
`0f0ff57f7e4e9e1aabc65d5e41079db09d84075a8dd486c4d16c1774a17eaf52`.
The existing build-73 IPA remains the matching device-test artifact. Changes are
confined to the diagnostic branch; the compat baseline is unchanged.
