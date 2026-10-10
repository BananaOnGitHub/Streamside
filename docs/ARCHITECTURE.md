# Architecture

## Request interception

The dylib uses public Objective-C runtime and Foundation entry points instead of
private Twitch symbols.

- Playback-token GraphQL bodies are normalized at `NSURLSession` task creation.
- HLS requests from Amazon IVS are intercepted through `NSURLProtocol`.
- `AVAssetResourceLoader` remains as a compatibility path for AVFoundation.
- Internal VAFT requests carry `X-TAS-Internal` to avoid recursive interception.
- URL-protocol image and HLS transport uses asynchronous `NSURLSession` tasks.
  Each protocol instance owns its active task; stopping cancels that task and
  prevents further client callbacks, including during reentrant response delivery.
  Manifest processing remains in the completion path, outside `startLoading`.
  Provider images use a separate session and completion queue from HLS: alternate
  token/manifest downloads cannot block emote delivery on the HLS queue.

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
image refreshes preserve it. Strip scrolling does not dismiss the keyboard. Each owned button receives its
suggestion or Recent action at creation; UIKit scroll indicators are never
passed target/action APIs during history refreshes.

Provider tiles also own a cancelling `UILongPressGestureRecognizer`: only its
Began event presents the same `TASEmoteUI.c` details sheet used by chat taps,
reading the current button metadata after cell reuse. Hold recognition cancels
touch-up insertion; failed holds/drags keep the existing scroll cancellation.
Composer image interactions use the documented iOS 17 text-item menu delegate
and the older attachment-interaction delegate on the exact `ChatInputView`.
Optional methods are added when absent, or chained only after a full ABI check.
Only a private-code U+FFFC whose attachment identity and metadata match the live
editor suppresses UIKit's generic image menu. These callbacks never open the
sheet: UIKit can request them before the library's hold threshold. Both tile
and editor recognizers explicitly use 0.5 seconds. The editor recognizer hit-tests
TextKit glyph bounds and private attachment identity, ignoring whitespace,
ordinary/native text and marked input. At touch-down it accepts only owned
attachment hits. For those touches, recognizers inside the editor wait for its
long press to fail, rather than recognizing the native image gesture alongside
it and producing extra context-menu haptics. Short taps and movement still fail
the standard long press. It does not cancel text-view touches. Only its Began event queues the shared sheet
on the next run-loop turn, coalescing requests and rechecking the attachment and
visible weak owner. Native/foreign attachments
and links retain Twitch's implementation or UIKit's default menu/preview;
selection, text storage, undo and animation bindings are not modified.
Successful composer presentation emits one light `UIImpactFeedbackGenerator`
impact; stale, cancelled, duplicate or failed requests do not. Tile holds and
the shared chat details presenter retain their existing feedback behavior.
API references: [text-item menus](https://developer.apple.com/documentation/uikit/uitextviewdelegate/textview(_:menuconfigurationfor:defaultmenu:)),
[text items](https://developer.apple.com/documentation/uikit/uitextitem), and
[attachment interactions](https://developer.apple.com/documentation/uikit/uitextiteminteraction).
Gesture priority uses the documented
[dynamic failure requirement](https://developer.apple.com/documentation/uikit/uigesturerecognizerdelegate/gesturerecognizer(_:shouldberequiredtofailby:)).

Details actions dismiss only their owned, currently presented navigation wrapper,
not Twitch's stream controller or an ancestor. Open in browser waits for the
[dismissal completion](https://developer.apple.com/documentation/uikit/uiviewcontroller/dismiss(animated:completion:))
before calling `UIApplication.openURL:options:completionHandler:`. This prevents
initiating a sheet transition while Twitch is leaving the foreground. An owned
association coalesces repeated actions during dismissal. The completion retains
only the URL (explicitly, because this is a C block), releasing it after launch
or skipping launch if the application is no longer active. It does not capture
any sheet/composer/stream controller or run dismissal on return. Copy and Done
retain their immediate-dismiss behavior and share the scoped wrapper guard.

Hide the window-level suggestion strip before presenting details. Its placement
function returns without raising it while a details request is pending or the
owning view controller (or a parent) presents any modal. This prevents image,
selection and timer updates from painting suggestions above a sheet while the
underlying editor remains first responder. Once dismissed, normal placement
restores suggestions if the original input is still focused and has matches.
The editor hold is installed once per input, replaced when its editor changes,
and detached/released with composer state. UIKit's
[hold-duration API](https://developer.apple.com/documentation/uikit/uilongpressgesturerecognizer/minimumpressduration)
owns timing and movement cancellation; no timer approximates touch duration.

The suggestion strip also adapts Twitch's per-chat autocomplete catalog into
the same metadata/result model. Native codes retain their native IDs and use
Twitch's validated input/change/send path. Scoped hooks suppress the stock
vertical colon selector in automatic and colon modes after the native catalog
is ready, while preserving other native completions. See
[NATIVE_EMOTES.md](NATIVE_EMOTES.md) for the runtime investigation,
queue/Swift bridging guards and device validation requirements.

The complete provider library is an inline section between native Recent and
account subscription emotes. Its heading, All / 7TV / BTTV / FFZ control,
Channel / Global control and grid move together in the native collection's vertical
scroll. The owned grid scrolls horizontally in five rows, with UIKit's horizontal
flow layout filling each column top to bottom. Provider changes reset the scope
to Channel. Picker snapshots sort by name ignoring capitalization across all
included providers and scopes, with an exact-name tie-break, before applying
the result limit. The lookup registry retains its exact byte order and distinct
case-sensitive chat codes; suggestions retain channel-over-global precedence.
Bind the container's stored palette,
which is itself Twitch's collection view. Scoped, ABI-validated flow-layout hooks
copy attributes to move the following native cells and headers below the full
panel. Direct cell queries and visible-rectangle queries use the same coordinate
translation; the latter maps the requested viewport back to native coordinates
before obtaining attributes. The native layout's content height increases by the
panel height. Empty sections are skipped when choosing the insertion point;
headerless sections use their first cell and native inset. With no following
cells, the library starts at the original native content height. Native section
indexes, models, cached attributes and section/content insets stay unchanged.
A fixed 296-point grid fits five 56-point cells and four 4-point gaps. Larger
libraries extend its horizontal content, while native cell reuse keeps only
visible columns active. The section reserves 410 points including controls and
padding, or 178 points for an empty-state label. Rotation changes the grid width,
not its row count. Outer vertical scrolling and catalog/image refreshes preserve
its horizontal offset; provider, scope and room changes reset the first column.
An isolated UICollectionView subclass permits cancellation of UIButton tracking
for horizontal swipes, sharing the Recent row's scrolling options. Native scroll
classes and the emote tap/insert path retain their existing behavior.
Height/section/start changes use the flow layout's own invalidation-context class,
explicitly invalidate both delegate metrics and layout attributes, and request
an immediate native layout pass before placing the transparent panel. Attribute
copies carry a placement-generation marker so direct and visible-header paths
cannot translate the same copy twice. The panel and horizontal grid clip their
contents at their own boundaries.
The entry and matching highlight follow Recent in both footer stacks and jump
the native picker to the inline section. Scroll position drives their selection.
Twitch's Swift availability updates replace all arranged views, so installation
verifies membership, not just a retained association. A scoped footer layout
hook reinserts owned slots after rebuilds without duplicating buttons, actions
or constraints. Native footer navigation keeps the panel in the same list.
Recent provider names occupy a horizontal row beneath the native Frequently
Used heading in the library's collection view, populated on every opening without requiring a Recent button
press. The row scrolls vertically with native sections and horizontally within
itself. Additional top inset reserves its space; native section navigation and
scroll-driven highlights remain intact. Scoped flow-layout hooks exclude the
owned inset from sticky-header pinning, retaining the native section start and
push-off boundary. Both element-array and direct header queries return copied
attributes; cached attributes and other collection views remain untouched.
Opening/binding the legacy palette and changing owned geometry coalesce a
next-run-loop layout settlement. This applies invalidation after the current
native layout returns, when a nested layoutIfNeeded can otherwise be deferred.
At most two passes accommodate a newly realized first header and its inline gap;
the callback does not schedule itself, reload native history, or move either
scroll offset. A closed/detached palette is skipped. This UIKit path remains
needed on Twitch 31.5: device observation shows dual horizontal/vertical
broadcasts using the legacy player/chat, while horizontal-only broadcasts use RN.
Build 84 covers the deferred-layout ordering in host tests; initial native
Recent visibility still needs device confirmation on the legacy picker.
The rendered first header's UILabel is checked against Twitch's localized
Frequently Used title. Only that header moves into the owned inset; the row
follows it and uses a transparent background. If no matching native heading is
present, the row retains its preceding position. Other section titles are not
moved into that space.
The row lives inside a transparent clipping view whose visible bounds stop at
the pinned header's lower edge. Its scroll-view size and horizontal offset stay
stable as it scrolls out; clipped emotes cannot draw or receive touches over the
title. This does not rely on the native header having an opaque background.
Per-section inset callbacks require their complete inspected Objective-C encoding.
While the provider row leads the viewport,
the native Recent indicator uses the existing selected colors, even with empty
native history; leaving the row restores Twitch’s current appearance. No native
section model or selected enum is edited. The Recent button includes the provider
row in its destination. Layout and image refreshes preserve the browsing offset;
empty history and replacement keyboards remove only the owned inset. The row is
part of the same native collection as the inline provider library.
The native history manager is never passed provider objects.

Provider snapshots contain copied values, never registry pointers. Image requests
are coalesced by provider URL, limited to eight at once, and retried after a
60-second failure delay. Thumbnails have a 2 MiB encoded-body acceptance limit,
dimension checks, and a 96-entry/16 MiB-cost in-memory cache. Cells are reused;
only visible thumbnails are requested. Controller references use Objective-C
weak storage, and late image completions notify surviving input views on the
main queue. Recent names are limited to 40 and are resolved in the current
channel, without persisting channel IDs, chat text, or URLs.

Chat animation recovery retains weak layer membership and uses a single
one-second timer only while provider animations are visible. It reuses Twitch's
player, checks foreground/window/ancestor opacity and clipping, and stops when
idle. Foreground hook retries resume those checks. It does not retain chat rows,
fetch images, reset frame positions or change native emote playback. Composer
GIF playback preserves finite long delays, including final-frame holds, and
accepts the decoder's 20 ms float rounding. See [NATIVE_EMOTES.md](NATIVE_EMOTES.md)
for inspected native timing behavior and recovery tests.

The inspected composer identity occupies an optional 56-byte span. Native
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
