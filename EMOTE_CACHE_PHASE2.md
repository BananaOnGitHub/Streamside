# Phase 2: bounded cache-first provider transport

Baseline: build 78, commit `8e32a286f1bce635e1900fbb596b8c863c5b6a24`.
Candidate diagnostic build: 79. Phase 3 overflow/retry work is **not included**.

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
Lookup-registry saturation falls through to existing bounded flight admission;
this does not repair the existing budget-refusal recovery contract (Phase 3).

## Cache correctness and deliberately conservative misses

Cache presence is not freshness. `ReturnCacheDataDontLoad` is not used as a
freshness test. A production `NSURLSessionDataDelegate` annotates only cache
responses **Foundation already proposed to store**, retaining Foundation's
original storage policy, response/data, and existing userInfo. It forwards the
passive Foundation transaction metrics to the previous diagnostic observer.

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

Local Linux production-path tests and iOS cross-compilation pass. The complete
suite and exact Hermes regression are rerun before packaging; results are
recorded with the final handoff. The Apple integration job and on-device cache
behavior are separate evidence, never inferred from warm-cache task counters.

## Short device check after host/platform gates

No new full scrolling investigation is requested. For build 79:

1. Launch on the same large-set channel. Open stationary, wait for visible images
   to finish, export A. Cache proposals/annotated should distinguish actual new
   cache entries from legacy warm responses. Do not clear the HTTP cache just
   to manufacture a favorable result.
2. Close and reopen stationary once; export B. Compare cache-first hits and
   admission-to-delivery buckets with the preserved 12-column/60-instance opening.
3. One quick forward/back movement and immediate close/reopen, then export C.
   Check bounded lookup/flight counts, cancellation, errors and successful visible
   rendering. No long catalog sweep is necessary.

These UI reports cannot by themselves prove that all eight slots were saturated
while a particular hit arrived, or measure decoded/displayed visibility. The
controlled eight-slot HTTP integration is the platform gate for that condition;
physical-device performance, Fabric attribution, animation and actual rendering
still need device observation. Phase 3 retains responsibility for general
budget-refusal retry/recovery and residual visible/offscreen queue priority.

References: Apple documentation for `cachedResponseForRequest:`,
`URLSession:dataTask:willCacheResponse:completionHandler:`, `NSCachedURLResponse`
and cache policies; RFC 9111 sections 4.1, 4.2 and 5.2; Apple's continuous-clock
documentation. No stale-cache override is used.
