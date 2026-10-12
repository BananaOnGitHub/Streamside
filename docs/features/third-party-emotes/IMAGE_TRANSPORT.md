# Provider image transport

All provider image surfaces share the transport implemented in [Streamside.c](../../../src/Streamside.c). It separates HTTP cache lookup from transfer admission and keeps each consumer's delivery/cancellation state independent.

This document concerns encoded HTTP responses and request lifecycle. Provider identity is owned by [Providers](PROVIDERS.md); decoded thumbnails and composer GIF caches have separate lifetimes in [Composer](COMPOSER.md).

## Sessions and entry points

The runtime URL protocol recognizes permitted provider image URLs. Synthetic Twitch image requests are first resolved through the registry to their provider route. Both request-based and URL-based native image task entry points are covered.

Internal requests carry `X-TAS-Internal` to avoid recursive interception. Provider images use a dedicated session; HLS uses a separate completion path because manifest processing may synchronously fetch alternate tokens/manifests.

The provider session configures a Foundation `NSURLCache` with 32 MiB memory and 128 MiB disk capacity at `StreamsideProviderImages`, eight per-host connections, 15-second request timeout, 30-second resource timeout, and a four-operation completion queue.

Those capacities are configured budgets, not guarantees of resident memory, actual retained bytes, or network throughput.

## Eligible sharing and identity

`image_public_request()` admits ordinary GET requests without body/body stream, Authorization, Cookie, or Range. Private/range/other requests do not enter public-image coalescing.

The group key is URL plus cache policy and complete explicit header dictionary. Equal URLs with different Accept or other headers remain different variants. Cache policy is normalized before comparison.

The scheduler stores at most 512 flights, each with 64 consumers. An identity-matched existing flight can be joined before a new cache lookup. Redirected chat/input requests can promote the flight to foreground priority.

## Cache-first lane

[TASImageCacheLane.h](../../../src/TASImageCacheLane.h) has a separate 512-group lookup registry and at most two workers. It owns no independent network downloader.

The lane groups identical variants and retains the consumers/request while querying Foundation. Eligible fresh hits call the normal protocol completion without occupying an active transfer slot. Ineligible or uncertain entries fall through to normal Foundation task handling.

Before a miss starts any transfer, all surviving consumers are admitted under the cache → transport lock order. This prevents a fast completion from outrunning the remaining consumers in the same lookup group.

Lookup saturation spills to ordinary bounded flight admission/overflow recovery. Session initialization happens in worker work rather than constructing a cache/session on the initiating UI thread.

Callbacks run outside registry locks. A stopped consumer is skipped even if it was already copied from a completed lookup. Cancelling an unstarted last-consumer group can release it immediately; a running lookup retains its own request until processing finishes.

## Foundation annotation, not a second cache

[TASImageCache.h](../../../src/TASImageCache.h) uses delegate data tasks because completion-handler data tasks bypass Foundation's `willCacheResponse` hook. Encoded chunks accumulate on the bounded active task and are delivered once through the existing flight completion.

Foundation decides whether to cache a response and its storage policy. The delegate adds timing/variant metadata only to a proposal Foundation already elected to store; it does not force `no-store` content into another cache.

Annotations record a boot-scoped epoch, sleep-inclusive monotonic tick, wall clock, conservative remaining freshness, and explicit request headers. These values stay inside cache metadata, not the diagnostic log. Reboot or uncertain clock/epoch information falls back to Foundation.

### Freshness

[TASHTTPCache.h](../../../src/TASHTTPCache.h) parses a conservative subset: strict IMF-fixdate, bounded integer Age/max-age, or Expires-based lifetime. Duplicate max-age, unsupported directives, field-qualified private, invalid extensions/dates, nonpositive lifetime, and no-cache/no-store cannot authorize direct serving.

For a Date-bearing annotation, current age is deliberately overestimated:

```text
currentAge = max(wallNow - Date, Age + fullTaskElapsed)
remaining = lifetime - currentAge
```

Lookup compares remaining lifetime with the greater of monotonic and wall elapsed since annotation. It does not count only lookup latency or renew the receipt when read.

Direct serving additionally requires a matching response URL/header variant, HTTP 200/nonempty body, admitted storage policy, compatible epoch, and usable metadata. Vary wildcard, cookie/authorization variation, uncertain implicit User-Agent variation, Content-Range, Pragma, conditional/directive-bearing requests, and expired clocks return to Foundation.

HTTP `private` response caching and an authenticated/private request are different concepts. This is a private app cache, but public-image sharing still refuses requests carrying private credentials.

## Date-less response receipts

Provider responses on the tested device sometimes supplied max-age but neither Date nor Expires. Build 79's direct annotation gate correctly refused them; build 80 isolated Date-missing as the first rejection. Build 81 compared both Foundation header-access APIs and response identities, establishing actual absence rather than a case-normalization guess.

[TASCacheReceipt.h](../../../src/TASCacheReceipt.h) supports these entries only after verified network provenance:

1. Stage the original cache proposal/received-response timing.
2. Require exactly one transaction, no redirects, and `resourceFetchType == networkLoad`.
3. Match task/transaction/proposal response URL, status, headers, and request URL.
4. Check ordered request/response timestamps and consistent monotonic/wall elapsed time.
5. Require successful completion and the same response/body/userInfo/storage policy still present in Foundation's cache.
6. Add the original network receipt without forcing an absent/evicted entry back into storage.

A cached callback alone is not network proof. Local-cache transactions cannot mint or refresh a receipt. Lookup never writes a new clock. Initial Age plus conservative task/receipt delay reduces freshness before storage; repeated reuse continues aging that original receipt.

One first-rejection counter is recorded per proposal. Successful late receipt annotation replaces its Date-missing rejection, preserving proposal accounting after callbacks settle.

## Shared scheduler and cancellation

The scheduler allows eight active transfers, at most six background. It chooses foreground before background and preserves generation/FIFO order within priority. These are admission limits, not “eight image views.”

Each protocol consumer has stopped/completed state. Completion snapshots consumers under the transport lock, clears the flight, then delivers outside the lock. Generations reject obsolete completions for reused slots.

When the last consumer leaves an unstarted flight, it is removed. When the last consumer leaves an already running flight, the bounded transfer may finish detached and populate Foundation's cache. A newly created view can rejoin it instead of restarting the same download.

Stopping one consumer never cancels another consumer's task. Delivery rechecks stop state, including a reentrant stop during response delivery. Queue cancellation, detached completion, rejoin, and transport error categories have separate counters.

## Overflow recovery

[TASImageOverflow.h](../../../src/TASImageOverflow.h) adds 64 waiting groups with at most 64 consumers each and a 30-second original deadline. It handles refused admissions; it is not another downloader or concurrency increase.

Identical variants coalesce without extending the deadline. A free normal slot transfers ownership directly from overflow into the existing flight registry, preserving original queue time, priority, and generation ordering.

One timer expires waiters; it does not poll/retry/create network tasks. Cancellation removes an individual consumer and releases an empty group. Expiry delivers one terminal timeout to surviving consumers. If both recovery and normal admission are full, the normal terminal failure path completes once.

## Reading timings

Keep the measured boundaries separate:

| Measurement | What it covers | What it does not prove |
| --- | --- | --- |
| Cache-lane wait | Admission to worker lookup | Network or decode time |
| Cache lookup operation | Foundation lookup and usability decision | Actual displayed pixels |
| Cache-hit delivery | Lookup admission through consumer completion | Decode/Fabric presentation |
| Transfer queue wait | Normal admission to task start | Task completion speed |
| Task completion | Started task through encoded-body response | Whether the transaction used network |
| Source-to-onLoad | JS source assignment through load callback | Pixel visibility or physical view identity |

Foundation transaction metrics distinguish local-cache from network work. Cumulative loads are not unique assets, mounted views, current flights, or simultaneous active tasks.

The recorded build-82 E→F delta added 197 direct hits and 18 Foundation tasks, all 18 local-cache transactions, with additional queue waits at most 250 ms. This supports warm reuse for that run. It does not establish that earlier multi-second waits were harmless or justify changing throughput.

## Tests and evidence

[Cache protocol](../../../tests/test_cache_protocol.py), [Annotation](../../../tests/test_cache_annotation.py), [Receipt](../../../tests/test_cache_receipt.py), [HTTP parsing](../../../tests/test_http_cache.py), [Overflow](../../../tests/test_image_overflow.py), and [Protocol](../../../tests/test_protocol.py) execute production helpers/lifecycle through controlled adapters.

[Foundation integration](../../../tests/test_foundation_cache.py) runs real Apple HTTP cache/revalidation on macOS. It is an explicit skip on Linux; `make test-foundation-cache` cannot skip missing Apple tooling.

The archive preserves [transport builds 71/72](../../archive/experiments/EMOTE_IMAGE_TRANSPORT.md), [cache builds 79–82](../../archive/investigations/EMOTE_CACHE_PHASE2.md), and [overflow build 83](../../archive/experiments/EMOTE_OVERFLOW_RECOVERY.md). Their failed delegate/task and Date-less hypotheses are historical, not current unfinished features.

[Feature map](README.md) · [Diagnostics](../DIAGNOSTICS.md) · [Testing](../../development/TESTING.md)
