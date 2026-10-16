# Provider WebP animation trial — 3.1.0 build 14

Development branch: `dev/3.1.0`, based on `5ab9e56`. The paused
`fix/rn-chat-gaps` investigation is unchanged. This trial changes image format
selection and presentation, not HLS, chat delivery, redemption handling, or
Hermes message/list instrumentation. **Build 14 passed the RN device checks.**
Legacy chat was subsequently tested on a vertical stream and exposed three
issues. Build 15 restored animation, but fast animations lag across native
surfaces. Build 16 adds read-ahead and composer timeline corrections; device
confirmation of the speed improvement is pending.

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

Build 14 bounds (build 16 changes are recorded below):

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

In build 14, the RN chat and RN library/info surfaces use this loader boundary.
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

Device acceptance is recorded below. Host tests establish the implementation's
allocation and lifecycle bounds; the device report establishes normal rendering
and interaction behavior on the tested installation.


## Candidate validation record

Implementation checkpoint: `862f354797430ea6fcf81e61241302f8ba835b84` on `dev/3.1.0` (build 14).
The final source suite ran 189 tests: 187 passed; Apple Foundation-cache and
Apple ImageIO-pixel tests skipped on Linux. Both ordinary and emote+demand
probe native variants passed layout/signature/fingerprint and defined-WebP-
implementation checks. Both DEB packages built. The exact donor settings and
compiled virtualization gate passed (32 snapshots and 7,344 layout calculations).
The Hermes graft chain is unchanged; these checks are regression evidence,
not on-device animated WebP acceptance.

The normal `0/0/0` candidate passed independent finished-IPA verification:

- Filename: `Twitch_31.6_Streamside_3.1.0-build.14_webp-animation_unsigned.ipa`
- Bytes: 194,487,453
- SHA-256: `565118e65769960e8099d1c872bcd76d4fb71ef9e479161dbfb2fb9e9fa630f3`
- Donor: original Twitch 31.6 (262821841498166537), supplied privately.

The source parser also admitted the four downloaded mhm/ono WebP variants
with matching frame counts/canvases and final 600/2,170 ms delays. No provider
artwork or private donor binaries are checked into the repository. Test pixel
fixtures are generated solid colors and transparent subrectangles.

The distributed IPA is unsigned and needs signing for installation. Build 14
subsequently passed device acceptance as recorded below.
The paused diagnostic branch has not received this renderer trial.

## Initial device acceptance — 2026-10-15

The tester accepted build 14 as working generally. Confirmed behavior:

- Correct animation pauses in incoming RN chat, own sent messages and the composer.
- Suggestions, library and emote info render correctly.
- Static, wide and transparent emotes render correctly.
- Scrolling, view reuse and channel switches work correctly.
- Returning from picture-in-picture to the main playback page works correctly.

The initial report accepted the WebP renderer. The later legacy checks below
established that this acceptance covered the RN paths, not legacy chat.

## Legacy follow-up — build 15, 2026-10-16

Testing a vertical stream exposed three legacy issues in build 14:

- Animated provider emotes remained still in chat, despite working elsewhere.
- Tapping an emote in a message such as `mhm ono YAY mhm ono YAY` could open
  another emote's details.
- Selecting a picker emote brought up the keyboard and displaced chat/input
  behind the player, making the input unreachable.

The donor's TwitchKit network image factories call
`FLAnimatedImage.initWithAnimatedGIFData:` (`@24@0:8@16`) for animated bodies.
The legacy `TWAnimatedImageLayer` consumes `posterImage`, `frameCount`,
`delayTimesForIndexes`, `loopCount` and `imageLazilyCachedAtIndex:`. Build 14
supplied these interfaces but only connected the new adapter to RN loading
and owned composer/thumbnail paths.

Build 15 connects the legacy factory to the shared ImageIO WebP template.
Only an already validated template admitted by a successful provider HTTP
response can replace the GIF factory's result. The check uses the immutable
encoded value because Swift's Data/NSData bridge can recreate the NSData
object; it does not claim URL provenance from a byte match. Admission expires
with the bounded template cache. GIF, unknown data, missing templates,
disabled emotes and incompatible method encodings retain the original factory.
The replacement follows initializer ownership: release the unused allocation
and return the retained adapter. There is no GIF conversion or additional
network path. Twitch's existing legacy display link, per-layer playhead,
visibility checks and loop recovery remain in charge of playback.

Legacy emote taps now inspect the displayed attachment layers' geometry and
synthetic identities. This avoids rebuilding a separate TextKit layout whose
positions can diverge after wide attachments or wrapping. Traversal respects
hidden/transparent/clipped ancestors and is bounded to 1,024 layers and depth
16. Unmatched/native taps continue to Twitch's original handler.

Picker insertion keeps Twitch's existing palette/hidden responder active.
The validated UITextInput edit and native change notification remain; the
unconditional `becomeFirstResponder` call is removed so selecting an emote
does not independently open the system keyboard during the palette session.

Host regressions exercise the production legacy factory's admission, bridged
data, initializer ownership, fallback and ABI checks; actual displayed layer
identity for repeated/wrapped emotes, gaps and visibility; and picker/suggestion
edits without focus changes. These checks do not replace on-device acceptance
of the three reported legacy failures. The paused chat-gap investigation and
its specialized instrumentation remain unchanged.

### Build 15 candidate validation

Implementation checkpoint: `54fe5b74bce3d8e76e30a8bf5c944c4b6964855d`.
The full suite ran 191 tests: 189 passed, with the two Apple-only integration
tests skipped on Linux. The exact donor/Hermes gate passed with 32 accepted
snapshots and 7,344 window calculations. Ordinary and emote+demand diagnostic
native variants passed artifact and defined-WebP checks; both DEBs built.
The finished normal `0/0/0` IPA passed independent verification:

- Filename: `Twitch_31.6_Streamside_3.1.0-build.15_legacy-emotes_unsigned.ipa`
- Bytes: 194,487,632
- SHA-256: `4fa343ae6032ad8d020410cf1f297fbd11a55738c001715acc9541bd04705a78`
- Donor: original Twitch 31.6 (262821841498166537).

This is the device-test candidate for legacy animation, repeated-emote info
taps and picker insertion on the vertical-stream layout. Device results for
build 15 are pending.

## Fast-animation follow-up — build 16, 2026-10-16

The tester confirmed that build 15 restored legacy chat animation, but fast
emotes such as `ehehe` ran slowly and lagged in chat, the composer, suggestions
and library. The info popup played correctly. That popup uses an image-only
WKWebView, independently of the shared native adapter.

The popular 7TV `ehehe` variant `01H5ECBJ080004C067KYDBPSQ2` has 277 frames,
each 20 ms, for a 5,540 ms loop (178,746 encoded bytes at 2x). Its parsed delays
already match the file. This identifies a representative fast asset, not the
exact channel variant observed on the tester's device.

The build-15 adapter only queued the requested frame on a main-thread cache
miss. Sequential players therefore paid a decode/display-tick wait at frame
boundaries. The owned composer clocks additionally discarded elapsed time
while waiting for decoded pixels, stretching the animation loop. The shared
four-frame cache also provided too little space for independently phased
consumers of the same asset.

Build 16 changes:

- Poster and cache hits trigger background preparation of three upcoming
  frames, before their display deadlines. Four moving demand windows can
  coexist per asset, without sharing playback positions.
- The hard frame cache remains 32 MiB globally, with at most 1,024 entries
  and 16 frames per asset. Eviction within an asset prefers frames outside
  its active windows, rather than repeatedly evicting another consumer's
  next frame. RN view buffering remains four frames.
- There is still at most one queued/running operation per asset, 64 globally,
  two workers and serialized ImageIO rasterization. Each operation makes at
  most 16 decode attempts and rechecks demand between attempts. An asset-wide
  one-second backoff prevents failed read-ahead from repeatedly retrying
  different frames in a broken source.
- The owned legacy/RN composer display links request 60 Hz. Their indexed
  WebP clocks preserve elapsed time through cache misses, retain the previous
  pixels until the current timeline frame is ready, and retry that frame on
  subsequent ticks. Encoded per-frame delays and long holds remain unchanged.
  Existing GIF cache-miss behavior and native chat/thumbnail players are retained.

Regression coverage includes 200 steps of four independently phased consumers
with every upcoming frame ready after the scheduled worker interval, bounded
decode counts, cache/job limits, loop wrap and failure backoff. The production
composer clocks are tested through decode misses and a 12.5-second hold. These
controlled worker checks do not measure real iOS ImageIO decode throughput;
`ehehe` speed and smoothness still need device confirmation across the reported
surfaces. Build 15's tap/picker fixes also await explicit device results.
