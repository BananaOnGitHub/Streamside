# RN provider library — builds 69–70

Build 68's unified inline suggestions were confirmed on device. Build 69 ports
the legacy provider library into Twitch 31.5's React Native emote tray. Build 69
was confirmed on device; build 70 fixes selected-state contrast, restores the
bounded five-row horizontal browser, and extends library backspace recognition.

The top of the library contains a horizontal recent-provider scroller. Its
first admitted snapshot is frozen for the library opening, keyed by channel
and Twitch's emote-picker session ID. Selections, own sent messages, and
provider catalog updates can update persistent recents without moving that
visible row. Closing and reopening resolves the saved names against the
current room again. History uses the existing `StreamsideRecentEmotes` key,
deduplicates names, and retains at most 40.

The main provider grid follows native Frequently Used and precedes channel
subscriber emotes. Its sticky header has All/7TV/BTTV/FFZ controls and then
Channel/Global controls. Changing provider resets scope to Channel. Selection
uses `textBase` fill with `backgroundBase` text, contrasting in both themes.
The outer provider section contains one 260-point row. A nested horizontal
FlatList virtualizes columns of five 52-point tiles, preserving image aspect.
Filter changes remount the horizontal list at its beginning; catalog size never
increases the outer vertical section. Native sections keep 52-point rows.
The footer adds a star section shortcut after native recents. Native footer
buttons retain their handlers; their section indices are translated around
the inserted provider section. Highlight follows the visible section.

Taps re-resolve the selected name and synthetic ID in the exact admitted room
before calling Twitch's existing `onSelectEmote` with an ordinary code string.
Long presses open an owned RN info sheet with the existing provider actions.
The emote button continues to open Twitch's library. Inline suggestion Off
does not disable library browsing. Disabling third-party emotes leaves the
native library intact.

## Confirmed donor seams

- Writable Metro leaf 4174 / factory 4178 exports `EmotePickerTray` (20057).
- It reads JSX runtime 245 for `emote-grid-list` and `emote-nav-tablist`.
  Only those exact type/test-ID pairs route to adapters. Context limits the
  implementation to the owned library session; other JSX forwards unchanged.
- Native `gridGetItemLayout` (20047) uses 52-point rows and 28-point headers.
  The adapter accounts for the recent header and the 88-point provider header.
- Native `appendToken` (37374) calls `trim()` on its argument. Insertion sends
  the code string, without a synthetic object or network/send payload change.
- The existing owned strip graft installs these adapters; original donor
  function bodies, metadata, constants and debug data remain preserved.
- Writable Metro leaf 4687 / factory 4691 exports `useChatComposer` (21555).
  Its native backspace callback 37375 submits updater 44613 to the same
  functional draft setter exposed as `setDraft`. It invokes the pure
  `smartBackspace` helper (19095, through barrel 3758) at the draft's end.
  Recognition uses `emoteTokenMap`, `cheermoteTokenImages`, and suggestion
  `emoteTokenAliases` from 3382. The owned adapter adds no React hook slots,
  modifies no catalogs and preserves every other native hook result field.
  It reuses the donor helper with the same native predicate plus exact provider
  `lookup(channel, code)`. Queued taps operate on the newest draft; the helper
  retains native space and surrogate-pair semantics. This footer follows the
  native end-of-draft behavior, not the keyboard's selection behavior.

Native bridge snapshots contain immutable catalog values for Channel and
Global. Room identity must resolve uniquely by ID or login; there is no
last-room fallback. Recents are recorded through validated library/inline
selection and the completed own-message display path. They are never added
by reading someone else's chat. Library methods are independent of inline
suggestion mode and gated by the admitted patch and feature state.

## Validation and device check

Owned RN tests cover section order, frozen recents through catalog changes,
reopening, provider/scope filters, wide images, stale-identity refusal, string
insertion, footer index translation/highlights, callback stability, empty
native catalogs, unknown rooms, feature disable and inline Off. Production C
tests cover bridge registration/ABI, snapshot ownership, persistence ordering,
manual sent codes, ambiguous scopes, retired IDs and disabled behavior.
The exact-donor graft verifier checks writable exports, type/test-ID seams,
row/header constants, insertion type, every unaffected function and handler,
branch/closure targets, footer hash and independent Hermes disassembly.

Install build 70 and fully restart Twitch. Open the library and confirm the
recent row, provider section placement, both controls, and new footer icon.
Select an emote and reopen to check recents refresh; confirm it stays fixed
while browsing. Check native channel/global footer jumps, wide/animated
provider tiles, insertion/preview, long-press info, inline Off and disabled
third-party behavior. Build 69's fundamental library behavior was confirmed.

Build 70 uses a synchronous exact-name lookup independent of inline suggestion
mode, instead of the suggestion search (which is disabled in Off and capped at
64 results). It admits only one occupied explicit room and performs no catalog
sorting or history mutation. Disabled, unknown or ambiguous rooms refuse.
Check selected fills on both filter rows, five-row sideways browsing with a
large channel catalog, native footer jumps, and deletion of provider/native
codes, ordinary text and emoji. Build 70 remains pending device validation.
