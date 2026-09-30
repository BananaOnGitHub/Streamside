# Architecture

## Request interception

The dylib uses public Objective-C runtime and Foundation entry points instead of
private Twitch symbols.

- Playback-token GraphQL bodies are normalized at `NSURLSession` task creation.
- HLS requests from Amazon IVS are intercepted through `NSURLProtocol`.
- `AVAssetResourceLoader` remains as a compatibility path for AVFoundation.
- Internal VAFT requests carry `X-TAS-Internal` to avoid recursive interception.

Authenticated startup GraphQL responses are never proxied.

## Per-stream ownership

Each observed `/channel/hls/<channel>.m3u8` master playlist creates or updates a
`TASStreamContext`. Parsing that master registers each exact rendition URL in a
bounded route table.

When a media playlist arrives, its URL selects the owning context before any ad
logic runs. The context owns:

- Channel and master URL
- Master playlist
- Alternate masters for `embed`, `popout`, and `autoplay`
- Active clean variant and its lifetime

Generation counters prevent a delayed network response from writing into a
context slot that has since been evicted and reused. Inactive contexts expire
after 30 minutes; the tables use bounded LRU replacement.

This ownership model is essential on iOS because Twitch can run the main/PiP
player and a muted channel-profile preview simultaneously.

## Ad handling

On an ad-bearing media playlist, the port:

1. Reuses a still-valid clean variant belonging to the same stream.
2. Requests alternate playback tokens in VAFT order.
3. Selects the matching or closest rendition.
4. If every alternate remains stitched, removes marked ad segments and serves a
   small blank media response for their segment URLs.

Unknown media-playlist URLs pass through without borrowing another stream's
state.

## Diagnostics

`TASDiagnostics` registers two runtime-created UIKit controllers and adds an
`Ad Block` navigation item to Twitch's `AppSettingsViewController`. No Twitch
settings data source is replaced or modified.

Logging is disabled by default and stored under the app's Application Support
directory when enabled. The log records only classified events and summaries:

- Interception transport and sanitized request path
- HTTP status and response size
- Master/variant ownership
- Segment and marker counts
- Alternate player type outcome
- VAFT fallback and suppression decisions

Query strings, fragments, headers, access tokens, GraphQL bodies, and manifest
contents are excluded. The file rotates at 512 KiB. Session counters remain in
memory and are included in the in-app report.

## Optional chat emotes

The saved third-party emote preference is read once at launch. When off, the
emote module installs no WebSocket or image-request hooks and makes no provider
requests. The existing Ad Block settings page remains available to turn it on.

When enabled, incoming IRC WebSocket text frames are scanned for known 7TV,
BTTV, and FFZ codes in the message's room. Synthetic entries are appended to
the IRC `emotes=` tag without replacing the message text or existing Twitch
emote ranges. Image requests for those synthetic IDs are redirected to the
provider CDN. The integration uses only three provider APIs and only loads
channel sets when its room ID is observed in chat.

Global and per-room name maps are distinct. Channel names win over global
names, with 7TV, then BTTV, then FFZ breaking provider collisions. Six room
maps are retained, with per-room and global entry caps. Inactive rooms expire
after 20 minutes; evicted synthetic IDs are kept for at most 45 minutes and
3,000 entries to let recently visible chat cells redraw. Failed fetches back
off from 60 seconds to eight minutes. Reload invalidates pending responses and refetches
global and recently observed channel sets. Clearing the cache discards all
owned entries and refetches lazily from the next chat frame. The module stores
no image files itself and does not clear Twitch's unrelated image cache.

The stream Chat Settings action sheet receives a Reload Emotes action. The
Ad Block page owns the enable switch and Clear Emote Cache action. UI and
transport hooks still need device validation against the target Twitch build.

## Signing layout

Both arm64 outputs contain 16 KiB of Mach-O header padding.

- `TwitchAdBlock.dylib` uses `@rpath/TwitchAdBlock.dylib` and is packaged for
  jailbreak injection.
- `Streamside.framework/Streamside` uses `@rpath/Streamside.framework/Streamside` and is
  packaged for sideloading. Its file-backed segments fill their existing 16 KiB
  ranges, and its compact ad-hoc signature ends at EOF so iOS signers can
  replace it cleanly.

Earlier rename trials inherited an unnormalized final 2.3.0 IPA. Comparing its
actual Mach-O bytes against working dev.8 exposed the segment-size regression;
the donor name itself is not an initialization requirement. Restoring the
normalized layout produced a launching migration candidate. This does not
prove compatibility with every signer or Twitch/iOS version.

`artifact_guard.py` records exact SHA-256, segment geometry, install/signing
identities, signature offsets/reservations, and framework metadata after the
build's normalization and signature update. Both binaries are normalized; the
jailbreak binary reserves at least 64 KiB and the framework uses the exact
16-byte-rounded compact signature size. Every CodeDirectory must cover the
entire unsigned code region, have the normalized executable range, and pass
all code-page hashes.

Receipts live alongside (not inside) the framework. Packaging requires the
receipt and independently validates the supplied bytes; it never silently
repairs them. Finished IPA/framework ZIP/source bundle/DEB native entries are
read back and compared byte-for-byte with their validated build inputs. A
layout or fingerprint mismatch aborts the packaging step. This verifies build
integrity, not certificate trust or on-device launch behavior after signing.

## Installation paths

For sideloading, the patcher removes obsolete dylib/framework commands, places
the verified `Streamside.framework` in the app's Frameworks directory, and injects
exactly one required Streamside load command. For a jailbroken install,
`TwitchAdBlock.dylib` is loaded into the `tv.twitch` process by a
Substrate-compatible filter. Rootful packages install under `/Library`;
rootless packages install beneath `/var/jb/Library`.
