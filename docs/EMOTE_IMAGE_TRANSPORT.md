# Shared provider image transport — build 71

The device report describes slow emote images in chat, composer previews and
the library, not only in the library browser. All three provider presentation
routes converge on Streamside's URL protocol after synthetic-URL redirection.
The existing paths already separated provider images from HLS completions, but
used the default shared HTTP cache and inherited each caller's request policy;
every concurrent request created a separate data task. These are concrete
optimization opportunities, not a measured diagnosis of the device's delay.

## Changes

- Reuse one dedicated provider session with a 32 MiB memory / 128 MiB disk
  `NSURLCache`. Public GET requests use protocol caching rather than inheriting
  a forced-reload policy from an outer loader. Foundation still enforces CDN
  expiration, validation, `Vary` and `no-store`; there is no unconditional
  permanent bitmap cache or speculative catalog-wide download.
- Coalesce concurrent public requests for the same URL **and identical headers**.
  Chat, input previews, recents and the library can share transport bytes while
  retaining their own existing decoder, image identity and completion handler.
  Differing header variants, explicit authorization/cookies, ranges and non-GET
  requests do not enter this path. Only the inner request is normalized.
- Limit the registry to 128 active flights and 64 consumers per flight. If either
  limit or URL allocation fails, use the existing independent request path;
  do not drop or indefinitely defer an image.
- Removing one consumer leaves the shared task running for the others. Removing
  its final consumer cancels and immediately retires that flight. A generation
  guard prevents its late completion from delivering to a reused slot.
- Use a provider-only completion operation queue with at most four concurrent
  operations and eight connections per host. HLS stays on its original separate
  session. Session initialization no longer takes the HLS registry mutex.

No JS bundle graft, provider format choice, dimensions, animation decoder,
library geometry, native-emote URL or chat/send behavior changes in this build.
The HTTP cache stores only the requested provider resources, in the app's cache
directory; log privacy is unchanged. Existing Clear Emote Cache still clears
catalog definitions, not images (its settings subtitle already says this).

## Evidence and runtime interpretation

The lifecycle harness executes the production transport against deferred tasks:
fan-out, individual/final cancellation, late completions, reentrant client stops,
errors, missing tasks, variant separation, unchanged special-request policies,
both registry caps, recursion prevention and independent HLS processing.
Configuration assertions cover the cache capacities and completion limits.
This is not an on-device HTTP-cache or performance benchmark.

Diagnostics add aggregate shared-load/coalesced/completed/error counts, plus
completion buckets: <=250 ms, <=1 s, <=5 s and >5 s. A shared load may be served
by the HTTP cache; it is **not** evidence of a new network download. Timings start
before task creation and finish before image delivery, excluding downstream
image decoding/rendering. Cancelled flights and independent fallback requests
are excluded from the completion buckets. There are no image URLs, emote IDs,
headers, bodies or per-emote histories in these new counters.

Device check: try a previously unseen static and animated provider emote in chat,
then type it into the input and open/reopen the library. Check both first-load
latency and reuse, animation startup, and rapid library dismissal. If images
remain slow while transport mostly completes in <=250 ms, investigate the native
RN image decoder/queue next rather than increasing download concurrency again.
