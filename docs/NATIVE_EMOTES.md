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

The third-party Recent row sits below Twitch's native Frequently Used title
and above its native history cells. The rendered first header's title is checked
against the app's localized `Frequently Used` string; Channel/other headers are
never repurposed. Its existing 48-point inset is reused by moving only the title
into the reserved space and positioning the row directly beneath it. Native
cell geometry, section models, navigation and sticky-header push-off stay intact.
If Twitch has no native Frequently Used header, the row keeps its preceding
position rather than borrowing a Channel heading. The row has a transparent
background so it shares the section's appearance.

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
