# Phase 2: bounded cache-first provider transport

> Completed investigation, preserved at `archive/rn-image-demand` and included
> in active `compat/twitch-31.5` build 87. The Apple Foundation and host gates
> passed; build-82 E→F recorded 197 direct hits and 18 additional local-cache
> tasks, with no new network fetches or receipt stamps. The user reported very
> fast loading. Earlier device-pending statements below are historical.
> Throughput remains frozen; overflow recovery is an independent correctness
> change. See [the branch closure](docs/DIAGNOSTIC_BRANCH_ARCHIVE.md#rn-image-demand-builds-73-87).

Baseline: build 78, commit `8e32a286f1bce635e1900fbb596b8c863c5b6a24`.
Initial candidate diagnostic build: 79; network-receipt fix: 82. Build 83 adds
isolated [overflow recovery](EMOTE_OVERFLOW_RECOVERY.md). Throughput changes remain deferred.

## Production path

Eligible public provider-image GETs retain the existing URL + exact request-header
identity. Ordinary Twitch outer reload requests still normalize to
`UseProtocolCachePolicy`. Explicit cache-only/revalidation policies are retained
and included in flight identity; conditional or cache-directive requests bypass
the direct-cache optimization but still use bounded shared transport when public.
Authorization, Cookie, Range, non-GET and body/body-stream requests retain their
independent Foundation path. HLS uses its separate session unchanged.

1. An existing flight is joined immediately, preserving foreground promotion,
   detached-flight reuse, independent cancellation and the 64-consumer bound.
2. Otherwise, admission enters a separate, fixed 512-group lookup registry with
   at most two worker pumps. Concurrent identical lookups share a group.
3. Public-image session/cache construction, `NSURLCache.cachedResponseForRequest:` and direct-cache delivery happen on
   those background workers, not the main thread or an image-transfer slot.
4. A verified fresh response is delivered through the same `protocol_complete`
   and stop-aware `protocol_deliver`, with original response metadata and data.
   It creates **no URLSessionTask** and occupies **no flight-registry entry**.
5. A miss/uncertain/revalidation result atomically admits the live consumer group
   to the original scheduler before any transfer starts. A fast first completion
   cannot outrun the remaining coalesced consumers. No callbacks occur while
   cache/transport registry locks are held.

The underlying transfer registry remains 512 flights, eight active transfers,
six background transfers, and 64 consumers per flight. No second downloader,
prefetcher, retry loop, stale-image fallback, or UI window clamp was introduced.
Lookup-registry saturation falls through to bounded flight admission. Build 83
adds bounded recovery when ordinary admission is full; it does not change throughput.

## Cache correctness and deliberately conservative misses

Cache presence is not freshness. `ReturnCacheDataDontLoad` is not used as a
freshness test. A production `NSURLSessionDataDelegate` annotates only cache
responses **Foundation already proposed to store**, retaining Foundation's
original storage policy, response/data, and existing userInfo. It forwards the
passive Foundation transaction metrics to the previous diagnostic observer.

The real Apple gate exposed an important integration distinction: the existing
completion-handler data tasks stored responses but did not invoke the cache
proposal hook. Shared (eight-slot bounded) image flights now use Foundation
delegate data tasks. A task-owned body buffer and copied completion block bridge
back to the existing one-shot flight completion; chunk assembly is synchronized,
and the buffer/block are released on completion. Independent restricted image
tasks and HLS retain their existing completion-handler path. No competing
downloader or additional active transfer was introduced.

Direct reuse requires a nonempty HTTP 200 response, permitted storage, matching
URL and exact original request headers, and trustworthy age metadata. Freshness
supports explicit `max-age` or `Expires` with a valid IMF-fixdate `Date`.
`max-age` takes precedence; private-cache `s-maxage` does not replace it.
`no-store`, `no-cache` (including field-qualified), invalid/conflicting directives,
unknown extensions, uncertain dates, `Vary: *`, cookie/authorization Vary,
implicit User-Agent Vary, Pragma, Content-Range and uncertain bodies/variants
all fall back to Foundation. Fresh `must-revalidate` content is usable;
expired content always goes through bounded Foundation validation.

Age is conservatively overestimated using the larger of apparent Date age and
Age plus the **entire task duration**. Remaining freshness decreases using both
wall-clock elapsed time and a sleep-inclusive continuous clock. A boot-scoped
epoch permits verified same-boot relaunch reuse; if boot identity is unavailable,
the fallback is process-scoped. Reboots, clock uncertainty and older/unannotated
cache entries take Foundation's original path rather than being served stale or
deleted. Foundation still owns actual validation (including conditional/304
processing) and all cache storage/eviction. This optimization is intentionally
not a full replacement HTTP cache engine or a guarantee of direct reuse for
every representation Foundation might consider fresh.

Cache-internal metadata is not diagnostic logging. Only aggregate counts and
time buckets are reported; no URLs, asset identities, request/response headers,
tokens, bodies, chat text or channel identities are emitted.

## Bounded diagnostics and timing interpretation

- Verified lookup hits/misses, coalesced lookups, cancellations, spills and
  directive/policy bypasses (which do not count as cache lookup operations).
- Lookup groups, consumer counts, scheduled/running worker budget and fixed
  registry bytes; bounded maxima and explicit limits.
- Aggregate miss reasons: absent, metadata, expired/clock, HTTP validation,
  variant, forbidden storage, unusable body.
- Foundation cache proposals versus successful annotations: distinguishes a
  delegate/metadata integration failure from a real cache miss.
- **Cache-hit admission-to-protocol-delivery**, cache-lane wait, and lookup
  operation durations are separate from transfer-queue wait and task completion.
  Hit timing is per delivered lookup group (oldest group's admission), not per
  emote/view; cancelled-only groups do not contribute delivery latency.

Existing task completion counters still include HTTP-cache responses delivered
by Foundation. They are **not network-only download times**. Decode/display and
JS source-to-onLoad remain downstream, distinct measurements.

## Validation and evidence boundary

`tests/test_cache_protocol.py` compiles the actual production lifecycle, cache
delegate, freshness logic, cache lane, and flight scheduler. Its controlled
Foundation adapter tests:

- A cache hit with all eight transfers stalled **and all 512 flights occupied**:
  one successful delivery, no ninth task, no flight refusal or admission.
- Identical cached and uncached concurrent consumers; independent cancellation;
  foreground promotion; an immediate completion during resume cannot create a
  duplicate transfer for the same lookup group.
- Cancellation before lookup, during hit/miss lookup, reentrant callback stop,
  active lookup abandonment/rejoin, and zero duplicate/late delivery.
- Unannotated/old-epoch/expired/clock-uncertain responses, no-cache/no-store,
  Vary/headers, cache-policy and conditional-request restrictions.
- Two actual pthread worker pumps, 20 repeated close/remount/rejoin cycles,
  the 512-group bound, immediate cancellation capacity recovery, and no transfer
  for abandoned misses. The ordinary production tests retain auth/range/POST,
  HLS isolation, priority, detached reuse and flight saturation coverage.

`tests/test_http_cache.py` compiles the production parser and checks dates,
leap years, weekday validity, directive syntax/precedence, invalid/conflicting
values, expiry and numeric overflow. This is not a source-string-only mock.

`make test-foundation-cache` is a mandatory **Apple Foundation** integration
gate. It compiles the same production lifecycle against real Foundation and a
local HTTP server: one warm origin fetch; eight delayed origin transfers;
cache-hit delivery before those transfers release; real ETag/304 revalidation;
and concurrent cached consumers. A macOS CI job runs this gate. Linux unittest
discovery explicitly skips it and must not be reported as Apple evidence.

The preserved RN build-78 regression gate still checks the real donor/Hermes
calculation and five-row fractional geometry. No RN library/graft code changed.
The compiled snapshot gate must pass before another device scrolling test.

### Current execution evidence

Local Linux suite: 102 tests, 101 pass and one explicit Apple-only skip. The
preserved real donor/Hermes regression passed 7,344 window calculations and 32
accepted compiled-runtime snapshots. Diagnostic iOS cross-compilation passes.

Apple CI run 37910936725 reached eight active transfers but failed the cached-hit
deadline: the original completion-handler candidate had zero cache proposals
and annotations. The delegate-task correction was published after explicit
diagnostic-branch approval, in commit `8a439c4d166c9c7ed56ec64c2e83ef5b3927aaaf`.
Its real Foundation gate **passed** on macOS 15 in CI run
[37912335269](https://github.com/BananaOnGitHub/Streamside/actions/runs/37912335269),
as did the build/ordinary test job. The gate confirms cached delivery within
1.5 seconds with eight delayed transfers active, one origin request for the
cached fixture across repeated consumers, and a real conditional HTTP 304.
This is Apple Foundation platform evidence, not physical-device/Fabric evidence.
The final diagnostic IPA is rebuilt from the corrected source; earlier packaged
completion-handler candidates must not be used as the Phase 2 baseline.

The Apple integration job and on-device cache behavior remain separate evidence,
never inferred from warm-cache task counters.

## Build 79 device result and annotation isolation

Phase 2 remains **unvalidated on device**. Build 79 reports A/B recorded 950
lookups, zero direct hits, and only two annotations from 793 Foundation cache
proposals. The A-to-B delta was 384 lookups/tasks: 333 metadata misses matched
333 Foundation local-cache transactions, and 51 absent misses matched 51 network
transactions. Cached responses were still entering transfer admission; these
were not 333 repeat downloads. The preserved library baseline held at 60 images
on opening/reopening, 130 peak while scrolling, and balanced dismissal mounts.

The annotation callback now counts one **first rejection** per proposal:

- Task-start metadata missing, invalid, or later than the current age clock.
- Non-public request, non-default cache policy, or explicit validation directives.
- Non-200 response; missing/invalid/future Date; invalid Age.
- Oversize Cache-Control; invalid or repeated max-age; no-cache; no-store;
  invalid extension delta; unsupported/field-qualified directive.
- Missing/invalid Expires, nonpositive freshness lifetime, or construction failure.

Counters are incremented under the existing metadata lock. Their sum plus
successful annotations equals proposals. Earlier failures do not evaluate later
gates, so precedence, freshness acceptance and Foundation fallback remain
unchanged. Only aggregate counts are reported; no header values, asset identities
or exception text are added. These counters cannot recover which condition
rejected historical proposals whose values were not retained.

`tests/test_cache_annotation.py` invokes the actual production callback for
33 response-policy cases plus every additional gate (42 calls per diagnostic
configuration). It checks the exact rejection bucket, one callback, proposal
accounting, preservation of original rejected responses and original userInfo,
and response/data/storage metadata for annotations. All 22 rejection buckets are
exercised. The same 33-case matrix also runs with real Foundation objects in the
mandatory Apple integration gate, alongside the eight-slot admission/304 test.

The matrix includes policy shapes sampled from public provider image GETs on
2026-10-09: 7TV's public max-age/s-maxage/immutable policy and FFZ's public max-age
policy annotate successfully. BTTV's repeated Cache-Control fields, combined as
`max-age=15552000, public,max-age=15552000,immutable`, hit the existing repeated
max-age rejection. That is a reproduced representative exclusion, **not evidence
that it caused the majority of the device failures**. Header normalization by a
particular Foundation version and other device gate failures remain observable
through the new counters. The parser has not been relaxed to force cache hits.

No further full scrolling test is requested. The compiled snapshot validation
rule remains mandatory for any diagnostic build. Annotation host/Apple tests
must pass before a focused device annotation check; Phase 2 cannot be declared
complete from fast Foundation cache-fetch timing alone.

References: Apple documentation for `cachedResponseForRequest:`,
`URLSession:dataTask:willCacheResponse:completionHandler:`, `NSCachedURLResponse`
and cache policies; RFC 9111 sections 4.1, 4.2 and 5.2; Apple's continuous-clock
documentation. No stale-cache override is used.

## Build 80 result and build 81 passive header comparison

Build 80 A/B isolates the first annotation rejection: all 168 proposals were
rejected as `Date missing`, with zero annotations and zero direct-cache hits.
On reopening, 85 additional lookups/tasks matched 85 additional Foundation
local-cache transactions and zero additional network transactions. The library
stayed at 60 JS images, range 0..11, with 60 library and 27 recent-image unmounts
at dismissal, successful loads on reopening and zero image errors. These reports
do not establish that the server omitted Date: they establish that the existing
header accessor returned no Date to the annotation parser. The accessor is
already case-insensitive; a capitalization defect has not been demonstrated.

Build 81 observes the proposed response and `task.response` independently for
Date, Cache-Control, Age and Expires. Each fixed field has exactly one outcome:
neither API, accessor only, dictionary only, both equal, both different,
ambiguous case variants, or uninspectable. A separate aggregate records whether
the task response is the same object, a different object, or missing. There are
60 fixed uint64 counters (480 bytes), no retained response/header objects, and a
maximum of 128 dictionary keys examined per response. Missing or incompatible
objects/keys/values and scans over the limit are uninspectable, not proof of
header absence. The scan uses case-insensitive NSString keys and checks value
types. Empty strings count as present; the existing freshness parser still
decides whether their values are valid. Observation precedes annotation, so
probe and proposal totals agree once callbacks settle.

The probe is compiled only with IMAGE_DEMAND_DIAGNOSTIC=1. It does not replace
the existing header accessor, synthesize dates, use dictionary values as a
fallback, relax freshness, alter Foundation cache storage, or change transport,
virtualization or retry behavior. Reports contain fixed labels and aggregate
counts only. The transport report buffer is 8192 bytes to retain the complete
comparison section; capacity-limited formatting remains bounded.

Host tests exercise every comparison outcome, all four fields, response identity,
missing responses, case variants, non-string keys/values, exact/over-limit scans,
complete/truncated reporting and privacy. The production callback still rejects
a dictionary-only Date and preserves the original cache proposal. Apple CI runs
the live HTTP saturation/304 gate with diagnostic probes enabled, plus real
Foundation response/dictionary checks and a deliberately disagreeing accessor
subclass. That subclass is a controlled test, not evidence of CFNetwork behavior
on the phone. Device results remain necessary to identify the actual mismatch.

Next device check after the host/Apple/compiled gates: restart Twitch, open the
library stationary and export A; close/reopen stationary and export B. Leave
the HTTP cache intact. No full scrolling sweep is requested. Phase 2 remains
unvalidated on device, and Phase 3 overflow/retry work remains outside this change.

## Build 81 result and build 82 network receipt path

Build 81 A/B confirmed absent Date and Expires through both Foundation APIs on
all 181 proposals. Cache-Control and Age agreed through both APIs; proposed and
task responses were the same object. Reopening added 90 local-cache responses,
zero network transactions, and zero direct hits. Phase 1 remained healthy at
60 library images/range 0..11 with complete dismissal cleanup and no errors.

Build 82 supports a missing Date only with cache-internal original network
receipt metadata. The response delegate captures wall and continuous ticks,
but that callback alone is not provenance. The original Foundation cache
proposal is delivered unchanged. After task metrics and successful completion,
metadata can be committed only for one complete network-load transaction,
without redirects, with matching response URL/status/headers and request URL,
ordered request/response dates, and consistent start/receipt/current clocks.
Missing metrics, cached/pushed/unknown loads, incomplete/mismatched timestamps,
clock jumps, errors and unproven 304 merges keep Foundation's path. A late
metrics callback cannot resurrect a completed proposal.

The existing URLCache entry must still match the Foundation-approved proposal's
response, data, userInfo and storage policy; an absent/evicted/replaced entry
is not forced into cache. The metadata-only replacement preserves the body,
response and policy. At most one proposal/receipt/proof is retained per bounded
active task and all are cleared at completion. No unbounded side registry or
second cache is introduced.

Persisted userInfo records the versioned network-receipt proof, original wall
and continuous ticks, corrected initial age, remaining lifetime, boot epoch and
request headers. Initial age includes upstream Age plus the larger wall or
continuous task-start-to-receipt delay; resident/body time is counted from that
original receipt. Lookup requires consistent receipt fields and a matching
epoch/variant, validates the explicit max-age/Expires policy, checks initial
age against Age, and subtracts the larger elapsed clock. No-cache/no-store,
invalid Date, invalid Age and uncertain metadata remain misses. Reopening is
read-only; an existing receipt is never restamped by a local-cache proposal.
Expired entries return to Foundation for validation, including conditional 304.
Existing unannotated entries gain no invented clock: they become eligible only
after a proven new network response. No forced cache clear/reload is added.

The production host lifecycle tests control only clocks/Foundation objects and
exercise direct reopen, exact expiration, unchanged clocks after local-cache
completion, same-boot epoch reconstruction, invalid/missing/future metadata,
26 provenance/completion refusal cases, Age, no-cache/no-store and counters.
Apple integration uses real Date-less HTTP, real transaction metrics and
URLCache userInfo, serialization of the metadata, direct reopen, an unannotated
local-cache response, expiration and a server-asserted conditional 304. Those
tests must pass before delivering build 82; device acceptance remains pending.

The aggregate staged/stored/fallback counters expose receipt progress without
reporting timestamps, identities, request/header values or URLs. A successful
late receipt commit replaces its provisional Date-missing rejection; annotation
and rejection totals partition all proposals once callbacks settle. Phase 3
overflow/retry work and RN virtualization remain outside this change.
