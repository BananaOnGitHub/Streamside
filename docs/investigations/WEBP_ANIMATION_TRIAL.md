# Provider WebP animation trial — 3.1.0 build 14

Development branch: `dev/3.1.0`, based on `5ab9e56`. The paused
`fix/rn-chat-gaps` investigation is unchanged. This trial changes image format
selection and presentation, not HLS, chat delivery, redemption handling, or
Hermes message/list instrumentation. Device acceptance is pending.

## Evidence and format selection

The inspected common 7TV assets have different final-frame durations in their
GIF and WebP encodings. These are measurements of the downloaded files, not
proof of which renamed/channel variant a particular device displayed.

| Name | 7TV identity | WebP last frame | GIF last frame |
| --- | --- | --- | --- |
| mhm | `01GWBD2YR00002CCPRV6KPX758` | 600 ms | 200 ms |
| ono | `01H6HR1QGR000FMZQ9NVXJ2FSQ` | 2,170 ms | 30 ms |

The second most popular variants inspected for each name had the same timing
difference. Restoring a clock's old ten-second cap fix cannot recover timing
absent from the encoded GIF. Chatterino's current 7TV loader selects WebP;
its desktop eager-frame cache is not copied here.

7TV now prefers advertised `2x.webp`, then `1x.webp`, before GIF/PNG fallbacks,
for both static and animated entries. BTTV uses its explicit `2x.webp` CDN
variant, checked with a static global emote and animated SourPls. FFZ retains
its advertised URLs; animated 2x/1x precede static 2x/1x. A static FFZ example
returned PNG even with a WebP Accept header, so no unsupported FFZ suffix is
invented. Native Twitch URLs and formats are unchanged.

WebP is not universally smaller. The sampled BTTV SourPls was 3,087,176 bytes
as WebP versus 1,062,103 as GIF. The trial preserves a bounded WebP input budget
rather than assuming every WebP is tiny. Different format URLs participate in
existing synthetic identity hashing, so old cached GIF IDs are not repurposed.
No extra timing download, transcoding, or rewritten HTTP body/cache is added.

## Shared decoder and playback ownership

[TASAnimatedImage.c](../../src/TASAnimatedImage.c) creates an actual UIImage
subclass backed by an ImageIO source and an immutable timing table. The WebP
container parser validates complete chunk lengths, canvas and frame bounds,
inner VP8/VP8L dimensions, and frame count before invoking ImageIO. ImageIO
owns compressed-pixel decoding, WebP compositing and disposal. Source count
must match the container; decoded images must have the full canvas dimensions.

Each frame is rasterized into a bounded RGBA bitmap on a background caller or
decode worker. Wrapping a lazy CGImage in UIImage alone would not guarantee
that decompression had left the UI thread. The system source is created with
its decoded-image caching disabled. ImageIO's private working memory is not
claimed to be part of the explicitly owned frame cache.

The adapter supplies the indexed frame/duration interfaces used by both RN's
animated image view and the existing composer/thumbnail clocks. Sharing the
immutable container/indexed cache does not share a playback position. Repeated
attachments retain independent index/elapsed state; the GIF compatibility
path keeps its existing independent FLAnimatedImage instances. There is no
conversion to GIF and no eager array of all decoded WebP frames.

Bounds:

- Encoded WebP: 8 MiB, at most 2,048 frames, dimensions at most 4,096 and
  at most 524,288 canvas pixels. Existing GIF preflight limits remain.
- Hard owned decoded-frame cache: at most 256 entries / 32 MiB globally and
  four cached frames per asset; LRU eviction. Displayed UIKit/RN references
  can independently retain pixels outside that cache.
- Template NSCache: configured 128 entries / 16 MiB of encoded bytes plus
  posters. NSCache budgets are advisory; visible views may retain containers.
- Main-thread frame misses: at most 64 queued/running jobs, one per asset at
  a time; a two-operation queue and serialized ImageIO rasterization. Misses
  return nil for the existing player to retry rather than decoding inline.
  Failed frame decodes back off for one second instead of retrying ImageIO
  at display-link frequency.
- RN's buffer is separately limited to four frames for this UIImage subclass.
  Other native images retain their existing buffer calculation.

Per-frame positive holds, including the last, have no ten-second upper cap.
Browser-compatible short-delay rules map at most 10 ms to 100 ms and 11–19 ms
to 20 ms. Provider emotes continue looping. Visibility, foreground/background,
IME, deletion and attachment reconciliation remain owned by existing clocks.

## Native boundary and failure behavior

The exact Twitch 31.6 React framework metadata was inspected:

| Class / method | Encoding |
| --- | --- |
| RCTImageLoader `_loadURLRequest:progressBlock:completionBlock:` | `@?40@0:8@16@?24@?32` |
| RCTUIImageViewAnimated `calculateMaxBufferCount` | `v16@0:8` |
| RCTUIImageViewAnimated `setMaxBufferCount:` | `v24@0:8Q16` |
| RCTUIImageViewAnimated `animatedImage` | `@16@0:8` |

Hooks require these complete encodings. The native loader still owns network
requests, progress, HTTP checks, scheduling, coalescing, cache and cancellation.
Only an admitted provider URL (or a known synthetic redirect) gets a wrapped
completion. A typed block capture supplies compiler-generated copy/dispose
ownership, including cancellation without a callback. The original request,
response, progress block and cancellation result are forwarded unchanged.
Native Twitch and unknown URLs bypass the wrapper. GIF/static/failed responses
retain native behavior. A WebP animation is substituted only when the native
buffer-limit hook is admitted as well.

System symbols, source count, full-canvas decode, class-preserving UIImage
initialization and bounded allocation must succeed. Failure preserves native
fallback rather than returning an invalid animation. A system that cannot
animate the format can therefore show a static fallback; this is not animation
acceptance. Runtime Render diagnostics report hook availability, created/refused
assets, decoded/failed frames and owned cache/job counts without URLs or text.

The current RN chat and RN library/info surfaces use this loader boundary.
Native composer previews and the UIKit suggestion/library thumbnails use the
shared adapter directly. Archived legacy native chat delivery has not been
reworked or device-validated by this trial.

## Validation boundary

The production-function host adapter exercises factory admission, timing,
background-only misses/rasterization, per-asset/global cache bounds, lazy
failure/retry, typed callback copy/dispose, cancellation without completion,
native URL/disabled-feature fallback and exact-ABI retry/idempotence. The
actual RN composer fixture also runs WebP data through independent clocks,
long holds, IME, hide/show, deletion and teardown.

The Apple-only ImageIO test decodes generated lossless WebP frames and checks
full-canvas pixels. It requires Apple frameworks/Xcode; a Linux skip is not a
passing decoder-pixel test. Native artifact validation additionally requires
the four WebP implementation symbols to be defined, rather than unresolved
weak host-fixture fallbacks.

Device checks must include mhm/ono loop timing in incoming/sent RN chat,
composer, suggestions, library and info; static/wide/transparent emotes;
scroll/reuse, channel switches, foreground/background, deletion, native Twitch
emotes and mixed provider formats. ImageIO alpha/blend/disposal and visible
performance remain device acceptance items.
