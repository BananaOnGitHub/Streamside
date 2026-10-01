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
`Streamside` navigation item to Twitch's `AppSettingsViewController`. No Twitch
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
requests. The existing Streamside settings page remains available to turn it on.

When enabled, incoming IRC WebSocket text frames are scanned for known 7TV,
BTTV, and FFZ codes in the message's room. Synthetic entries are appended to
the IRC `emotes=` tag without replacing the message text or existing Twitch
emote ranges. Image requests for those synthetic IDs are redirected to the
provider CDN. The integration uses only three provider APIs and only loads
channel sets when its room ID is observed in chat.

Global and per-room name maps are distinct. Channel names win over global
names, with 7TV, then BTTV, then FFZ breaking provider collisions. Six room
maps are retained, with up to 4,000 names per room and 2,500 globally. Provider
JSON is parsed only for nonempty HTTP 200 responses up to 8 MiB. Diagnostics
separate HTTP, transport, empty/oversized body, JSON and schema failures, and
normal channel 404 responses; only status, byte and entry counts are recorded.
Inactive rooms expire
after 20 minutes; evicted synthetic IDs are kept for at most 45 minutes and
3,000 entries to let recently visible chat cells redraw. Failed fetches back
off from 60 seconds to eight minutes. Reload invalidates pending responses and refetches
global and recently observed channel sets. Clearing the cache discards all
owned entries and refetches lazily from the next chat frame. The module stores
no image files itself and does not clear Twitch's unrelated image cache.

The stream Chat Settings action sheet receives a Reload Emotes action. The
Streamside page owns the enable switch and Clear Emote Cache action. UI and
transport hooks still need device validation against the target Twitch build.

## Composer integration

`SSComposer.c` hooks the exported `ChatInputView` UITextView delegate bridges,
footer actions, and clipboard actions, validating complete Objective-C method
encodings before installing them. It does not construct Swift emote models.
`SSComposerModel.h` maps UTF-16 positions between original names and image
attachments. Only attachments carrying Streamside's private code attribute are
expanded; native Twitch attachments and text attributes are retained. Preview
substitutions are excluded from undo registration. Scoped undo/redo expand names
before invoking the original manager. Marked text is left to UIKit.

Keyboard edits, including autocorrection, retain UIKit's original displayed
ranges and selection. Scoped main-thread getters provide expanded text and a
detached `NSTextStorage` snapshot to Twitch's synchronous validation, while its
didChange callback receives expanded text without replacing live storage.
Selection callbacks do not expand or redraw the editor. Preview updates are
debounced until callbacks settle, leave the active word as text until committed,
and retain existing attachment attributes to avoid rewriting identical content.
The snapshots apply only to the exact composer editor during those callbacks;
ordinary reads, other editors, and marked text retain their native behavior.

Suggestion and Recent strips use an owned `UIScrollView` subclass that allows
button tracking to be cancelled when a horizontal drag begins. Stationary taps
retain the emote button's touch-up action. New results reset the scroll offset;
image refreshes preserve it. Strip scrolling does not dismiss the keyboard.

An owned UIKit collection view overlays the existing keyboard's content area
when its third-party footer button is selected. The native footer and native
library actions remain available. Provider changes reset the scope to Channel.
Recent provider names occupy a horizontal row prepended to the native library's
collection view, populated on every opening without requiring a Recent button
press. The row scrolls vertically with native sections and horizontally within
itself. Additional top inset reserves its space; native section navigation and
scroll-driven highlights remain intact. While the provider row leads the viewport,
the native Recent indicator uses the existing selected colors, even with empty
native history; leaving the row restores Twitch’s current appearance. No native
section model or selected enum is edited. The Recent button includes the provider
row in its destination. Layout and image refreshes preserve the browsing offset;
empty history and replacement keyboards remove only the owned inset. The row is
part of the hidden native collection while the third-party tab is open.
The native history manager is never passed provider objects.

Provider snapshots contain copied values, never registry pointers. Image requests
are coalesced by provider URL, limited to eight at once, and retried after a
60-second failure delay. Thumbnails have a 2 MiB encoded-body acceptance limit,
dimension checks, and a 96-entry/16 MiB-cost in-memory cache. Cells are reused;
only visible thumbnails are requested. Controller references use Objective-C
weak storage, and late image completions notify surviving input views on the
main queue. Recent names are limited to 40 and are resolved in the current
channel, without persisting channel IDs, chat text, or URLs.

The optional 56-byte composer identity was inspected in Twitch 30.4.2: native
palette selection checks its +16 word for nil and reads its UInt32 ID at +0.
Only those primitive words are read, after checking the runtime field span.
No Swift string is dereferenced or interpreted as an Objective-C object.

The 3.0.0 app/bundle display name is **Twitch Streamside**. The future logo is
pending and must support UIKit dynamic appearance/background and tint. Current
icon assets remain intact and their package hash remains a required check.

## Signing layout

Both arm64 outputs contain 16 KiB of Mach-O header padding.

- `Streamside.dylib` uses `@rpath/Streamside.dylib` and is packaged for
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
`Streamside.dylib` is loaded into the `tv.twitch` process by a
Substrate-compatible filter. Rootful packages install under `/Library`;
rootless packages install beneath `/var/jb/Library`.
