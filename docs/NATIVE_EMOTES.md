# Unified composer emote selector

The Streamside horizontal strip searches Twitch's own per-chat autocomplete
catalog alongside the existing 7TV, BTTV and FFZ registry. Automatic and colon
modes use the same results and selection path. The native emote keyboard,
provider tab and scrolling third-party Recent row retain their existing behavior.

Third-party image IDs now derive from channel scope, emote name and provider
image URL, independently of request order or app launch. They use a separate
15-digit namespace from the old sequential IDs. This prevents Twitch's
persistent synthetic-URL image cache from displaying a previous session's
bitmap under a new emote's dimensions. A detected hash collision is rejected
rather than remapped; retired IDs keep their original image routes.

Picker views retain the displayed image record while visible and only apply
setters when their URL or image changes. Cache eviction and unrelated image
notifications no longer clear/restart an animation. Chat recovery is limited
to provider `ImageAttachmentLayer` instances: its attached
`TWAnimatedImageLayer` uses unlimited loops and re-evaluates native visibility
when paused. Native Twitch animation behavior remains unchanged. The inspected
30.4.2 setter (`0x100004644`) copies finite GIF loop counts, the display callback
(`0x100004808`) stops on countdown exhaustion, and removal (`0x10000452c`)
pauses the layer; the runtime hooks use selectors, never those addresses.
Those methods are in the main app executable. Its display callback builds its
duration table from every `delayTimesForIndexes` entry through `frameCount`,
including the last frame; no last-frame timing exclusion was found in the
checked-in source history. Composer playback formerly rejected delays over ten
seconds. It now retains all finite valid delays and tolerates ImageIO's float
rounding at the 20 ms decoder minimum; missing/nonfinite/invalid delays still
fall back to 0.1 seconds.

Layout/image callbacks are insufficient if an attached chat layer pauses later.
A weak `NSHashTable` tracks only provider animation layers, with one one-second
timer in common run-loop modes while any are visible. Checks require the active
application, nonhidden/nontransparent ancestors, a live window and intersection
with every clipping ancestor and the window. Recovery calls Twitch's existing
`updateAnimationState`, repairs a zero provider countdown, and never resets the
decoder, frame index or timing table. The timer invalidates when no tracked
provider animation is visible; existing foreground hook retries or a subsequent
provider layout/image callback restart it. Detached members remain weak for
reattachment; empty/native-reused members are removed. Diagnostics report only
aggregate bindings/resumes/checks.

## Twitch 30.4.2 investigation

These findings come from the decrypted 30.4.2 app and its bundled TwitchKit
framework. Addresses below are unslid analysis addresses, not runtime hooks.

| Component | Observed behavior |
| --- | --- |
| `Twitch.EmoteManager` | Owns native `allOwnedEmoteSets`, channel/user sets, subscription state and availability. Its catalog properties are private Swift values, not Objective-C getters. |
| `TwitchKit.TKChatEmote` | Native model with Objective-C `identifier`, `code`, `modifiedEmotes`, `assetType` and `isRegex` getters. Codes and identifiers remain native strings. |
| `Twitch.ChatConnectionController` | Owns `emoteManager` and `emoteAutocompleteManager`. Native catalog publication at `0x104313df8` / `0x104313e0c` supplies the same emote array to both. Initialization does the same at `0x104314c00` / `0x104314c34`. |
| `Twitch.ChatEmoteManager` | Exposes `initWithEmotes:` and `resetWithEmotes:`, but internal publication calls Swift worker `0x1012b0efc` directly. Swizzling those Objective-C wrappers alone would miss it. |
| `Twitch.ChatEmoteAutocompleteManager` | Builds its `emotes` array on `backgroundQueue`. Entries are its private `EmoteInfo` class, containing a Swift String code and Foundation URL. Worker `0x101001130` clears, populates and sorts the array. This is the native selector's searchable library. |
| `Twitch.ChatSuggestionsListController` | UIKit table data source reads the native match's results; rows are private Swift tuples. Native selection calls a Swift protocol witness. Constructing those match/row values or invoking that witness from fabricated storage is unnecessary. |
| `Twitch.ChatInputView` | `textViewDidChange:` loads its delegate with `swift_unknownObjectWeakLoadStrong`, then calls the native input delegate. Its weak existential is not an Objective-C weak pointer. |

This integration takes the autocomplete catalog after Twitch has populated it.
It does not independently combine subscription tiers, fetch emote sets, add
locked palette entries or implement GraphQL requests. Global/default,
channel-specific, subscription, modified and other native codes appear whenever
Twitch publishes them for this chat/account. The native picker remains the
authority; the integration does not promise access to every displayed locked
emote in Twitch's broader subscription discovery keyboard.

## Catalog adapter and ownership

Only the inspected app version is enabled. Runtime checks validate class names,
ivar offsets, instance spans and the Swift value-witness sizes for Array, String
and URL before reading any field. Missing symbols or incompatible layouts keep
the native vertical selector available and report a waiting bridge.

The adapter resolves Swift's existing metadata accessors and
`_bridgeAnythingToObjectiveC` dynamically. The latter's two-argument Swift ABI
is declared in the upstream [Swift runtime implementation](https://github.com/swiftlang/swift/blob/main/stdlib/public/runtime/DynamicCast.cpp).
It bridges actual native values into NSArray, NSString and NSURL, rather than
decoding string internals, guessing tagged array storage, or constructing Swift
model values. No Swift framework dependency or executable patch is added.

Snapshots run asynchronously on the exact autocomplete manager's serial queue.
The UI thread receives an owned code-to-metadata dictionary. The bridged NSArray
is retained with it, preserving the old immutable buffer and copy-on-write
ownership when Twitch publishes another list. A generation check discards late
results after switching connections. The input delegate provides the matching
standard or Skyline chat context; responder ancestry also supports inspected
chat views. A global singleton or the last background room is never substituted.

Native metadata has `name`, Twitch's `url`, the original CDN `id`, and a `native`
marker. It never enters the synthetic provider-ID registry. Native image
requests are restricted to HTTPS `static-cdn.jtvnw.net/emoticons/` URLs already
provided by Twitch, with the existing response/image size limits.

## Search, suppression and insertion

The full provider library has an entry immediately after native Recent in the
emote keyboard footer (first among emote tabs when Twitch omits Recent). It opens
the scrollable emote grid with All / 7TV / BTTV / FFZ and Channel / Global
controls; every provider change resets Channel. Native footer actions restore
the native palette, while backspace keeps the provider browser open.

Twitch 30.4.2's Swift footer availability worker (`0x101981f1c`) calls its
stack replacement helper (`0x1045a7480`): remove every arranged view, then add
only the native array. Streamside's retained button association survives that
removal. Checking only that association previously prevented reinsertion,
leaving the complete panel unreachable. Installation now checks both actual
stack memberships, reuses the same button/action and matching highlight, and
inserts them after Recent. A scoped footer layout hook catches Swift rebuilds
that bypass the Objective-C apply wrapper. Owned slots use the inspected native
40-point width / 3-point underline, and selection/theme restoration only changes
UIKit appearance, never Twitch's Swift selected-section model. Diagnostics
include the footer layout hook and creation/restoration counts.

Twitch 30.4.2's `EmoticonPaletteView.scrollViewDidScroll:` Objective-C wrapper
(`0x102fff498`) calls the Swift worker at `0x102ffe780`. The worker calculates
native section anchors and publishes a native selection byte (`0`, `1` or `2`)
through the reactive subject at its tail (`0x102ffefb4`–`0x102ffefc8`). It has no
provider-section value. Allowing that publication inside the added gap and then
repainting our shortcut made Recent compete with the provider highlight.
The scoped scroll hook therefore measures the current inline section first and
returns before the native callback only while the library owns the visible
section and its shortcut highlight exists. Native callbacks resume immediately
before/after the section, when the menu closes, and when the shortcut is missing.
Other collections retain their original callback. Native section models and
footer actions are preserved; no new Swift selection byte is fabricated.

Device testing rejected that scroll-only fix in build 32. Native Swift/reactive
footer paints can bypass the hooked scroll and `apply:` methods, so selection
also has a renderer-boundary guard. The UIKit tint/background hooks pass through
unchanged unless the receiver is one of the six associated native footer views,
still belongs to that state's current footer, and the library owns selection.
Native requests update the retained native-color snapshot, but display the
stable inactive tint and clear native highlight bars. Streamside's own styling
bypasses the guard. Active `apply:` calls no longer restore native highlights
temporarily; theme changes are captured and applied to the provider shortcut.
Leaving the library disables guards before restoring the latest native colors.
Replaced/unbound footer views pass through; newly bound views get their own
current appearance captured. Diagnostics report both guards and blocked writes.

Both composer modes search the complete captured native catalog and existing
provider libraries with case-insensitive prefixes. Native codes win exact
name collisions. Sorted native results alternate with provider results in a
bounded 64-tile horizontal window; more specific typing searches the full
library again. A bare colon searches with an empty prefix. Marked text, URL,
mention and mid-word boundary rules remain unchanged.

The vertical selector is suppressed only while its connected composer is
completing a colon token, the native catalog is ready, and a supported composer
mode is active. A scoped UIKit layout hook hides its view and collapses its
owned height constraint. Its data source keeps the original row counts: Twitch's
asynchronous completion reloads the table and scrolls to row 0 whenever its
Swift match contains results. Reporting zero rows made that scroll raise a
UITableView exception, including after edits/backspace. Leaving completion restores native
visibility and height. Mentions, commands, unrelated selectors and disabled
suggestions remain native. The native table's Swift match is never modified.
Restoration only changes presentation. `viewIfLoaded` can return a UIView
wrapper rather than the table, so sending `reloadData` to it crashed when an
emote selection ended the colon completion. No reload is needed because the
data source stays native. Host tests use a wrapper that rejects table methods.

Selection revalidates native codes against the current connection's snapshot.
It inserts the code through the existing validated UITextInput edit and native
didChange path, leaving native formatting, attachments, history and send
tokenization to Twitch. Provider choices continue through the existing registry,
preview, send and Recent implementations. Native names are excluded from
provider preview substitution, including names that collide with provider codes.

Exact provider codes at the caret's end become attachments on the next run-loop
turn after UIKit applies the edit and selection. There is no typing debounce or
image-download gate: bounds and the original code attribute reserve the space
immediately, even without a bitmap. Image completion fills the same attachment
with the downloaded image. A shared transparent RGBA pixel hides UIKit's
missing-image box while loading; it never counts as a completed download.
Image replacement invalidates layout/display, preserving the live text and caret.
Provider GIF previews retain their cached animation record and share one 30-fps
display link per visible input. It follows the GIF's per-frame delays, requests
frames through an attachment-local FLAnimatedImage decoder capped at four cached
frames and invalidates only the
changed attachment character's display. Frame updates do not rebuild attributed
text, recalculate layout or move the caret. Playheads survive ordinary edits,
image refreshes and cache eviction; active keyboard/IME transactions are skipped.
Hidden/detached editors stop their clock, while deletion and clipboard/send
expansion drop their playback bindings. Static and native attachments do not
enter this provider animation path.
Each attachment's decoder reuses the downloaded GIF data; it never shares the
thumbnail decoder's moving frame-cache window. Suggestions beside the caret and
repeated copies of an emote can therefore play at independent positions without
evicting one another's frames. Ordinary refreshes reuse the attachment decoder;
only replacing its source animation creates another. A failed local decode
keeps the static preview instead of borrowing the thumbnail decoder.
A caret inside a literal word or an overlapping selection keeps that word editable;
marked composition is never substituted. Typing beyond an exact code restores
literal text if the resulting word no longer matches.

Keyboard backspace deletes the one displayed attachment while native validation
sees its full code in an isolated expanded snapshot. The emote-menu backspace
flushes pending previews, then uses the editor's `deleteBackward` rather than
expanding codes and deleting a single letter. It retains UIKit's selection and
composed-character deletion. If an unfocused editor omits its didChange callback,
the resulting logical text is forwarded once to Twitch's native change handler.

The third-party Recent row sits below Twitch's native Frequently Used title
and above its native history cells. The rendered first header's title is checked
against the app's localized `Frequently Used` string; Channel/other headers are
never repurposed. Its existing 48-point inset is reused by moving only the title
into the reserved space and positioning the row directly beneath it. Native
cell geometry, section models, navigation and sticky-header push-off stay intact.
If Twitch has no native Frequently Used header, the row keeps its preceding
position rather than borrowing a Channel heading. The row has a transparent
background so it shares the section's appearance.
The inline library waits for the first native header's title and geometry before
choosing its section boundary. An unrealized, empty-title or zero-height header
is pending, rather than proof that Recent is absent. Pending native layout is
completed before reserving the library gap; otherwise insertion is deferred to
a subsequent layout. This avoids moving native Recent cells behind the library
before their header appears. Observations survive offscreen header recycling and
reset when the palette is rebound. Prepared headerless and empty collections
still receive the library without creating native section models.
An owned transparent UIView clips the row at the rendered Frequently Used
header's lower edge during vertical scrolling. The pinned title therefore stays
clear even with a transparent native header. The full-height scroll view moves
inside that viewport without changing its horizontal offset or cancelling a
swipe; the clipped portion also falls outside UIKit's touch area.

The third-party Recent row snapshots saved history on the first visible layout
of each emote menu opening. Selection/send still saves history immediately;
editing, timer ticks, tab changes and image updates only refresh thumbnails in
the existing buttons. Their order and horizontal scroll position stay stable
until the menu is closed and reopened. Footer window detachment also ends the
snapshot session, so a rapid reopen of the same UIKit menu loads current history.

Diagnostics report bridge readiness, selector hook installation, native catalog
snapshots/count/misses, native insertions and suppression transitions. They do
not store account identifiers, channel identities, codes or chat contents.

## Validation

Host tests exercise mixed prefixes, native-name precedence and identifiers,
bare-colon results, missing catalogs, bounded interleaving and presentation-only suppression
in automatic, colon and disabled modes. Existing composer tests cover UTF-16
mapping, autocorrection, attachments, strip touches/scrolling, Recent actions and
native sticky headers. Package validation still checks the normalized 16 KiB
segments, load-command identity, signature reservation and exact framework bytes.

The Linux build cannot run Twitch/UIKit or exercise the Swift runtime bridge
on an iPhone. Device validation must confirm a nonzero native catalog count,
native selection/send, account-owned subscription availability, connection
switches, stock colon suppression, mentions and commands before publication.
