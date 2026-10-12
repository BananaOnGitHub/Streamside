# VAFT playback interception

The playback core is a native adaptation of pinned VAFT solution 24. Its purpose is to keep each player's playlist decisions attached to the stream that produced them.

[Streamside.c](../../src/Streamside.c) implements the request hooks, stream tables, manifest handling, alternate-token requests, and synthetic segment responses. The browser source is retained under [upstream](../../upstream/vaft-ublock-origin.js); [Upstream](../UPSTREAM.md) explains the port's differences.

## Request interception

`normalized_graphql_request_copy()` limits handling to the `gql.twitch.tv` host and recognized playback-token bodies. `normalized_graphql_body()` recognizes PlaybackAccessToken / StreamAccessToken / streamPlaybackAccessToken markers and changes playerType to popout.

Unrelated authenticated startup/account requests retain their native request/response path. The port observes selected Twitch headers in process memory for alternate playback requests; it does not proxy login responses or persist those headers in diagnostics.

The session-configuration adapters register the runtime-created URL protocol. `protocol_can_init()` admits recognized Twitch HLS, remembered ad-segment URLs, and enabled provider images, while rejecting requests marked `X-TAS-Internal`.

The AVFoundation compatibility path changes an admitted asset URL to `tashttps`, then uses `AVAssetResourceLoader` to fulfill it. Playlist URLs are rewritten relative to the correct base and custom scheme where required. Amazon IVS interception uses Foundation's request path rather than a private Twitch player symbol.

## Stream ownership

Each observed `/channel/hls/{channel}.m3u8` master establishes or refreshes a `TASStreamContext`. `register_variant_routes_locked()` records each exact rendition URL against that stream slot/generation.

| Bound | Current value |
| --- | --- |
| Stream contexts | Eight |
| Active rendition routes | 256 |
| Retired route observations | 64 |
| Remembered ad-segment URLs | 256 |
| Inactive stream lifetime | 30 minutes |
| Active clean-variant reuse window | Ten minutes, subject to successful clean revalidation |

Context replacement clears its routes/owned strings. Generation-bearing `TASStreamRef` checks prevent a delayed alternate-master result from writing into an evicted/reused slot.

An exact media-playlist URL selects its owner before ad handling. Unmapped URLs do not borrow the newest stream or current PiP context. Retired-route reasons and ages help explain misses without recording the URL.

This is essential when main playback, PiP, and muted profile previews overlap. Per-channel contexts were introduced in 2.0.3 after single-global-state builds could substitute one player's content into another.

## Alternate-player algorithm

An ad-bearing mapped media playlist takes this path:

1. Reuse the same stream's active clean variant only while it remains within the reuse window and fetches without known ad markers.
2. Obtain alternate masters in VAFT order: embed, popout, autoplay.
3. Match the original resolution/frame rate, or select the closest admitted rendition.
4. Fetch that variant and accept it as clean only if its playlist lacks known ad markers.
5. If a cached alternate master fails, discard it and permit a fresh attempt for that player type.
6. If all candidates remain stitched, use the retained fallback candidate when available and suppress its remembered ad segments.

`request_access_token()` uses the pinned persisted-query hash and player/platform pairing. Autoplay uses the Android platform setting; the other alternate player types use web. Stream and alternate-master caches remain scoped to the originating context.

`has_ad_markers()` checks the broad stitched marker and MIDROLL/midroll variants. These are the implementation's known markers, not a guarantee that every future Twitch advertisement uses them.

## Segment fallback and manifest rewriting

`strip_ad_segments()` identifies the source's non-live EXTINF entries, remembers their following segment URLs, and removes Twitch prefetch lines. It does not simply delete every segment line and shorten the playlist.

Remembered ad segment requests receive the port's small blank media payload. Manifest durations/URIs otherwise remain in the rewritten flow. This is suppression through synthetic responses, not a second live player.

Relative segment/key/playlist URLs are resolved using the selected manifest's base, including after an alternate swap. Using the original base for a replacement variant would route content incorrectly.

If no clean alternate is available, fallback behavior depends on the available candidate and known marker/segment representation. An unknown/unmapped variant retains its native route rather than using another player's backup.

## Cancellation and callback ownership

The URL-protocol instance owns its task and stopped/completed associations. Start uses asynchronous `NSURLSession` work. Completion performs manifest processing and delivers through the existing client callbacks.

`stopLoading` marks stop before cancelling/detaching. Delivery checks stop state around response/data/finish callbacks, including a client that calls stop reentrantly during response delivery.

Internal token/manifest fetches use the recursion guard and the HLS completion path. Provider images have a separate session/queue; an ad-bearing playlist's alternate work cannot block emote response callbacks on that same queue.

The legacy asset-loader path remains a compatibility mechanism with its own native request fulfillment. It should be exercised separately when a Twitch port changes player routing.

## Failure and privacy

Invalid ownership does not authorize a replacement. Failed alternate requests are classified by status/response availability without printing tokens/manifests. Missing allocation/data or an unsupported path preserves the native behavior where the adapter can do so.

Temporary labels identify channels/playlists in diagnostic events; raw authorization, client-integrity, device/session headers, query strings, and manifest contents are not logged. Playback header state is transient runtime state, not evidence that no credentials ever pass through the process.

## Tests and release evidence

[Protocol tests](../../tests/test_protocol.py) exercise production manifest routing, asynchronous stop/delivery, recursion, and fallback contracts. [Privacy tests](../../tests/test_privacy.py) verify label/log exclusions. [Tool tests](../../tests/test_tools.py) cover packaging/injection boundaries.

Earlier release evidence established tested preroll handling on the 30.4.2 configuration. Clean playback or zero ad-marked counters in a 31.5 session does not prove preroll/midroll suppression. Release acceptance needs an actual ad-bearing playback case and its observed result.

[Architecture](../ARCHITECTURE.md) · [Diagnostics](DIAGNOSTICS.md) · [History](../HISTORY.md) · [Upstream](../UPSTREAM.md)
