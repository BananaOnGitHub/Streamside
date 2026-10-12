# Suggestions, provider library, and recents

The compact suggestion strip and the manual emote keyboard share definitions but serve different interaction paths. Twitch remains the authority for native/subscriber emotes and its own history.

RN integration lives in [ProviderEmoteStrip.js](../../../src/rn/ProviderEmoteStrip.js) and native exports in [TASEmotes.c](../../../src/TASEmotes.c). Legacy integration lives in [SSComposer.c](../../../src/SSComposer.c).

## Suggestion modes and matching

Automatic mode starts at a token end after two non-colon characters. Colon mode requires a leading `:` and can search with an empty prefix. Off restores native suggestion behavior and leaves the manual provider library available.

Selection must be collapsed and at the token end. URLs, mentions, embedded colons/slashes, U+FFFC attachments, and mid-word positions do not start owned completion. Queries are bounded to 96.

Search is a case-insensitive **contiguous substring**: `awa` finds `wawa`. It is not fuzzy character-order matching. Rendering/insertion still resolves exact case-sensitive codes.

Native names win exact-code collisions. Ordering differs by architecture:

- RN combines current native map entries and provider results, sorts by case-insensitive name with an exact-name tie-break, and retains at most 64.
- Legacy sorts native results and interleaves them with sorted provider results in a 64-tile window.

These algorithms should not be described as one shared interleaving rule.

## Native Twitch catalog authority

RN reads the current input's `emoteMap` and native URL templates. It honors the animation preference when selecting the native template. It does not fetch subscriber sets itself.

Legacy resolves the exact connection/autocomplete manager. Runtime admission checks classes, ivar spans/alignment, and Swift Array/String/URL value-witness sizes. The input delegate is a Swift weak class existential, not an Objective-C weak pointer.

The bridge uses existing Swift metadata and `_bridgeAnythingToObjectiveC` to obtain actual NSArray/NSString/NSURL values. It does not decode String internals or manufacture private match tuples. Snapshotting runs on the manager's serial queue; the bridged array is retained with the owned code-to-metadata dictionary so copy-on-write publication cannot reuse a buffer as false identity.

Only codes Twitch publishes for that chat/account are offered. A locked item visible elsewhere in the native subscription-discovery palette is not proof that it belongs in the autocomplete snapshot.

## Native autocomplete takeover

RN replaces verified writable leaf exports for `EmoteTextInput`, `useAutocomplete`, and `ChatAutocompleteTray`. Only native emote autocomplete is filtered while owned completion is active; mentions/commands remain native.

The autocomplete adapter adds no React hook slots to the existing donor call sequence. It also hides already retained emote matches before Twitch creates its send handlers, so a pre-takeover highlighted match cannot still be confirmed accidentally.

Legacy suppression changes presentation only: hide the connected selector and collapse its owned height while an admitted colon completion owns it. Native row counts/match state remain unchanged. Reporting zero rows had caused Twitch's asynchronous “scroll to row 0” behavior to raise an exception. Restoring a UIView wrapper must not send it table-only `reloadData`.

Off, unsupported catalog admission, or leaving the relevant completion restores native presentation.

## Insertion and stale-state protection

RN's `Composer` context records channel, draft, focus, native text, selection, completion span, and current mode. `caretFromEdit` handles text/selection event-order differences; later selection events override an inferred caret.

Before insertion, the row is re-resolved against fresh configuration/catalog state. The adapter checks current channel/draft/selection, send eligibility, ban/timeout state, result identity, and remaining text capacity. A stale visible row cannot insert into a different draft or room.

Insertion replaces the current prefix with the exact name and a space when needed, then calls the existing draft setter. Native/provider recognition and send serialization remain Twitch's responsibility.

Legacy revalidates its catalog and uses admitted UITextInput editing plus native did-change. Neither integration constructs a Swift token model to insert a suggestion.

## RN manual library

`LibrarySession` is keyed by explicit channel and `emotePickerSID`. It obtains immutable channel/global metadata sections and creates scoped context around Twitch's original tray.

The adapter routes only verified JSX leaf surfaces: `emote-grid-list` and `emote-nav-tablist`. The provider section is inserted after native Recent when present. A footer shortcut navigates to it; the ref proxy adjusts native section indices rather than changing native category data.

The outer vertical provider section has an 88-point header and one 260-point content row. Its header contains the title and All / 7TV / BTTV / FFZ plus Channel / Global controls. Provider changes reset scope to Channel.

The inner list scrolls horizontally in columns of five 52-point tiles, filled top-to-bottom. Viewport width determines 3–12 columns via `floor(width / 60)`. `initialNumToRender` and batch size are columns + 1; window size is 3.

Names use 11-point secondary text, a one-line trailing ellipsis, and a fixed 32-point thumbnail band. Accessibility and insertion retain the full name. Labeling does not change tile/column geometry or synthetic identity.

### Fractional interval correctness

The owned layout callback derives both interval endpoints from the same stride:

```js
offset = cellWidth * index;
length = cellWidth * (index + 1) - offset;
```

Returning `length = cellWidth` independently can leave a binary-floating-point gap. At 370/6 points, one old endpoint was 739.9999999999999 while the next began at 740. Twitch's unchanged overlap search then failed to identify the overscan end and fell back toward the full catalog, growing seven columns at every stationary adjustment.

Build 78 changed the owned interval calculation, not RN's window algorithm, visual widths, batching, cache policy, or network concurrency. The maintained compiled check executes the donor's actual overlap/window functions with the production callback.

The recorded device baseline stabilized at range 0..11 and 60 live library JS image instances for the tested 168-column catalog; scrolling had a 26-column mask/130-instance peak. These are observations for that fixture/run, not a universal maximum or a count of physical native image views.

## Recent history

`StreamsideRecentEmotes` stores at most 40 names. Choosing a provider emote revalidates its current room/name/ID before updating history. The name is moved to the front; unavailable names are omitted when resolving a new snapshot.

The first admitted Recent snapshot is frozen for an open menu, including an empty list. Inserts and catalog refreshes do not reorder that row until reopening. Twitch's native history is not cleared or replaced.

The RN provider Recent row is an owned header above native entries. Legacy places its provider row beneath the localized Frequently Used heading, shares native scrolling/background, and clips beneath the sticky header.

## Legacy inline library geometry

The UIKit picker retains native section models and cached attributes. Streamside copies/adjusts returned cell/header coordinates, extends content height, and translates visible-rectangle queries to reserve its owned gap.

It does not synthesize a Swift section-selection value. The horizontal provider panel and footer shortcut coexist with native categories. Cached flow-layout metrics must be invalidated when owned height changes; unrelated collections pass through unchanged.

A newly bound palette with zero native sections is **not** treated as an already prepared empty section. Build 86 defers the owned gap until sections arrive; otherwise an early section-zero gap can prevent the Recent heading/cells from realizing at all. Prepared headerless sections and temporarily empty already observed models remain distinct.

## Legacy footer and interaction lifecycle

Twitch can rebuild native footer stacks through Swift paths that bypass a hooked wrapper. A retained button association is insufficient: the adapter checks actual stack membership and repairs its button/highlight slot.

Provider selection guards only the associated current footer views. Native tint/background writes update retained native-color snapshots but do not overwrite the provider-owned active appearance. Leaving the section disables guards before restoring current native colors and the provider shortcut's inactive tint.

Keyboard reparenting can move the palette outside the input's ancestor chain. Binding the known palette container early allows lifecycle callbacks to resolve the weak input owner and insert/repair the footer synchronously, even during dragging when a default-mode timer would wait.

Owned scroll views permit button tracking to cancel on horizontal drag. Stationary taps retain insertion; long presses cancel touch-up insertion. Neither dragging the strip nor updating thumbnails should dismiss the keyboard.

## Backspace, details, and fallback

RN wraps Twitch's functional draft setter and `smartBackspace`, extending recognition with current provider lookup even when suggestions are Off. Native token aliases and cheermotes remain recognized. Provider preview names delete as whole tokens.

Library selection passes an ordinary string to the donor's existing append-token path. Details use registry metadata and the shared provider card. Missing bridge/snapshot admission returns the original tray; failed installer assignments restore all original leaf exports.

## Tests and historical evidence

[RN strip](../../../tests/test_rn_strip.py), [RN library](../../../tests/test_rn_library.py), [RN backspace](../../../tests/test_rn_backspace.py), [Recent snapshots](../../../tests/test_recent_snapshot.py), [Legacy library](../../../tests/test_composer_library.py), and [Native picker](../../../tests/test_native_picker.py) cover their production adapters through fixtures.

[Compiled virtualization validation](../../../tools/validate_rn_snapshot.py) is required for RN library changes/ports. Its 1,584 window scenarios complement host checks; neither is a replacement for device mounting/display/cancellation evidence.

[Calculation investigation](../../archive/investigations/EMOTE_DEMAND_PHASE1B_CALCULATION.md) · [RN library port](../../archive/experiments/RN_LIBRARY_PORT.md) · [Legacy Recent investigation](../../archive/investigations/LEGACY_RECENTS_DIAGNOSTIC.md)

[Feature map](README.md) · [Composer](COMPOSER.md) · [Testing](../../development/TESTING.md)
