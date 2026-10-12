# Composer

The composer must show images without losing the literal emote code Twitch needs for validation, editing, clipboard operations, and sending. RN and legacy UIKit solve this at different boundaries.

[SSComposer.c](../../../src/SSComposer.c) owns the legacy editor integration and shared suggestion preference/history. [TASRNComposerUI.c](../../../src/TASRNComposerUI.c) adds presentation and composition guards to Twitch's native RN input. The Hermes composer adapter supplies provider recognition maps rather than replacing Twitch's tokenizer.

## RN: extend recognition, preserve the draft

The active input is `twitch_rn_emote_input.TwitchEmoteInputView`, with native `TwitchEmoteAttachment` objects. [TASRNComposerPatch.h](../../../src/TASRNComposerPatch.h) connects the input's original code-to-ID map to the synchronous `emoteMap` export.

`rn_composer_map()` scans the bounded literal draft, resolves exactly one explicit known room, and adds up to 128 admitted provider codes. Native map entries win exact-code collisions. It returns a copied map only when additions are present.

Twitch keeps its draft, selection, tokenization, storage, and native image loading. Provider IDs use the ordinary stable identity, not the RN transcript width alias. The native URL-based image task is redirected as well as request-based tasks; build 61's placeholder-only trial showed why covering only request overloads was incomplete.

### Attachment identity and bounds

`attachment_number()` verifies the expected class, URL field span, Swift string bridge, synthetic CDN prefix, and registry metadata. An association caches recognized provider identity, including zero for native/unknown attachments.

The bounds hook calls the original implementation first. For admitted providers with finite supported aspect ratio, it changes width relative to the original height and leaves height, baseline, and paragraph styling intact. Native/unknown attachments retain the original bounds.

This is a native composer attachment seam. It does not describe Fabric transcript placeholders or the chat `EmotePart` width patch.

## Unconfirmed keyboard input

iOS can expose a full-looking provisional prediction before it is committed. Treating that provisional code as final allows a native setter to build an emote prematurely.

The inspected donor's change delegate checks `markedTextRange`, but `setValue:` and `setEmoteMap:` can rebuild attachments independently. The current guard covers change/selection callbacks and both prop setters.

While the exact editor has marked text:

- Delegate events and value props are held.
- Provisional draft values are discarded, not queued for replay.
- Only the latest recognition map is retained per input; an explicit nil map has its own sentinel.
- Native UIKit composition remains in control.

After the native delegate reconstructs committed text, `flush_map()` clears the stored map before calling the original setter, then synchronizes previews. A cancelled prediction therefore cannot replay its suggested full value. A later map replaces an earlier deferred map.

This is a composition boundary, not a timeout or a rule that every emote must wait for a space. Confirmed input uses Twitch's tokenizer. Device checks established the reported inline-prediction guard; broader keyboard/IME behavior should still be exercised when the donor changes.

## RN GIF previews

Native still-image behavior remains available for unsupported formats. Independent animation is limited to admitted GIF bodies:

| Bound | Current value |
| --- | --- |
| Encoded GIF body | At most 2 MiB |
| Canvas | Dimensions at most 4,096; total area at most 524,288 pixels |
| GIF structure | Complete blocks/trailer; more than one and at most 300 frames |
| Encoded-byte cache | 128 entries, 8 MiB cost limit |
| Watched inputs | At most eight weak owners |
| Attachments per input clock | At most 128 |
| Estimated decoder working set | At most 16 MiB per synchronized input |
| Lazy decoder frame cache | Four frames |
| Display-link target | 30 fps per visible input |

[TASRNComposerModel.h](../../../src/TASRNComposerModel.h) validates container structure without decompressing it. Each repeated attachment has independent decoder/playhead state, so the working-set budget counts repeated previews rather than assuming shared encoded bytes imply one decoder.

The owner is enrolled before its first decoder exists. When image bytes arrive, synchronization can start the original pending attachment immediately. Build 63 had width and animation but missed cold-download startup; build 64 corrected this ordering.

Frame delays preserve finite values at or above the decoder's rounded 20 ms minimum, including long final-frame holds. Missing/nonfinite/invalid values use 0.1 seconds. Display-link elapsed time is capped at 0.25 seconds per tick; hiding or background time is not replayed as a huge advance.

Only changed attachment character ranges are invalidated. Animation does not rewrite text or move the caret. Marked input pauses synchronization/advancement. Detachment, invisibility, empty preview sets, and deallocation stop clocks and release owned decoder/attachment state.

## Legacy UIKit: two representations

The legacy `ChatInputView` editor contains U+FFFC attachment characters. Owned provider attachments carry `StreamsideEmoteCode`; Twitch's native attachments and unrelated attributes do not.

`expanded_copy()` expands only that private code attribute back to its literal name. [SSComposerModel.h](../../../src/SSComposerModel.h) maps positions between expanded UTF-16 spans and displayed single-character attachments.

An expanded code of length N removes N-1 positions from the displayed coordinate space. `ss_display_position()` and `ss_plain_position()` map selection/edit positions in both directions. Native attachments remain length one.

### Native validation snapshots

Twitch's validation can synchronously read `text` and `textStorage`. During the exact main-thread validation callback, scoped getters expose expanded text and a detached `NSTextStorage` snapshot. The original displayed range/selection still belongs to UIKit.

The scope is a stack-like `NativeRead` record for the exact editor. Nested calls restore the previous scope. Ordinary reads, background reads, other editors, and marked text do not observe a temporary global draft.

The native did-change bridge receives expanded text without replacing live storage. Selection callbacks do not expand/redraw the editor. UIKit applies its own keyboard edit and autocorrection range before the owned preview update runs.

### Preview timing and deletion

Exact admitted codes outside an overlapping selection become previews on the next run-loop turn after UIKit finishes the edit. The current implementation does not debounce typing or wait for a bitmap.

A private transparent pixel prevents a missing-image box while bounds/code identity already reserve space. Download completion updates the same attachment and invalidates layout/display without rewriting the whole draft or moving the caret.

The token-safety helper keeps a word editable when the caret is inside it or a selection overlaps it. Exact completed codes at the token boundary can convert immediately. Provider names colliding with native codes remain under native authority.

Both keyboard deletion and the emote-menu backspace use the editor deletion path for owned previews, including unloaded placeholders. Clipboard operations and sending expose literal names. Preview substitution is excluded from undo registration; scoped undo/redo expands names before invoking the original manager.

## Legacy thumbnails and GIF ownership

Legacy composer thumbnails use an in-memory `NSCache` with a 96-entry / 16 MiB cost limit and at most eight concurrent owned requests. Visible image views retain their image record and only receive setters when source/image identity changes. Eviction or an unrelated refresh does not clear/restart a visible animation.

Preview GIF decoders are separate from caret-adjacent suggestion-image playback. Sharing a decoder had allowed one surface's lazy-frame consumption to interfere with another. Attachment-local decoder state and bounded lazy frames preserve independent clocks.

One 30-fps display link per visible input repaints changed attachment ranges. Long frame delays remain valid. Expansion, deletion, hiding, editor replacement, or teardown removes obsolete previews and stops clocks.

The legacy and RN budgets are not interchangeable; they use different storage and native adapters.

## Per-input lifecycle

Legacy state associates the current editor, room, native catalog snapshot, suggestion strip, picker binding, preview records, and hold recognizer with its own owner. Rebinding detaches an old editor's recognizer/state.

RN JS contexts track the exact channel/draft/selection and clear pending selection on blur or channel/draft changes. Native animation state weakly refers to its owner. Foreground retries can install classes loaded later and resynchronize visible owners.

Details presentation hides the window-level legacy suggestion strip while a pending or parent modal owns the surface. Normal placement restores it only if the original input remains focused and has matches. Hold and dismissal mechanics are in [Emote details](EMOTE_DETAILS.md).

## Tests and historical evidence

- [Composer tests](../../../tests/test_composer.py): UTF-16 mapping, edits, native validation, undo, clipboard, and marked input.
- [Preview tests](../../../tests/test_composer_preview.py): placeholder/image arrival, frame timing, and lifecycle.
- [RN composer tests](../../../tests/test_rn_composer_ui.py): provider-only bounds, GIF admission, first-download ownership, provisional callbacks/props, and cleanup.
- [Composer details tests](../../../tests/test_composer_details.py): private attachment identity and gesture/presentation scope.
- [Catalog compatibility tests](../../../tests/test_catalog_compatibility.py): explicit authority and native layout guards.

[RN preview trials](../../archive/experiments/RN_COMPOSER_PREVIEW_TRIAL.md) preserve the placeholder, URL-overload, width, animation, cold-start, and provisional-input corrections. [History](../../HISTORY.md) records the earlier legacy validation/undo and decoder-isolation work.

[Feature map](README.md) · [Picker](EMOTE_PICKER.md) · [Architecture](../../ARCHITECTURE.md)
