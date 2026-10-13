# 3.1.0 build 2 — RN composer emote holds

Branch: `dev/3.1.0`. Target donor: Twitch 31.5 (`262752111271985979`).
The RN input previously left provider attachment holds to UIKit's generic image
menu. This trial routes those holds to the same provider-details sheet used by
the legacy composer. Device acceptance is pending.

## Native seam

[TASRNComposerUI.c](../../src/TASRNComposerUI.c) uses its existing admitted
`TwitchEmoteInputView` editor and `TwitchEmoteAttachment` identity bridge. A
synthetic provider ID must resolve in the registry, and the exact attachment must
still occupy a single U+FFFC character in the live attributed text. No draft,
selection, tokenization, React state, or sending behavior is replaced.

The existing per-input preview target also owns one 0.5-second hold recognizer.
It is installed for visible inputs independently of GIF decoding, so static and
cold attachments can open details. The owner remains weak; teardown detaches the
recognizer and releases any pending attachment alongside the preview state.

Touch admission uses TextKit glyph bounds after subtracting text-container
insets. A nearest glyph outside its actual rectangle does not count. Ordinary
text, whitespace, native/unknown emotes, marked text, detached inputs, and an
already-presented modal do not enter the provider hold route. Only recognizers
inside that editor wait for an admitted provider hold to fail.

The exact RN owner class receives two optional UIKit delegate hooks:

- `textView:menuConfigurationForTextItem:defaultMenu:` suppresses the default
  image menu for a live owned attachment.
- `textView:shouldInteractWithTextAttachment:inRange:interaction:` declines its
  generic attachment interaction.

Existing methods require full matching type encodings; absent methods are added
only to that class. The recognizer requires the attachment hook and, when
`UITextItem` is available, the item-menu hook. A missing or mismatched hook leaves
the native route available. Native attachments and other text items call the
original delegate implementation, or use UIKit's default configuration when
Twitch had no implementation.

The hold queues one presentation on the next run-loop turn. Before presenting,
it rechecks the owner, visible editor, marked text, exact attachment identity,
current metadata, and competing modal. A removed or rebuilt attachment cannot
open stale details. [TASEmoteUI.c](../../src/TASEmoteUI.c) supplies the existing
provider sheet and its actions. One light haptic follows successful presentation;
a rejected presentation produces none. Diagnostic output reports both hook
states and the number of sheets shown.

## Verification and device acceptance

[test_rn_composer_ui.py](../../tests/test_rn_composer_ui.py) runs the production
helpers with controlled Objective-C ABI adapters under address/undefined-behavior
sanitizers. Its ten cases cover geometry, GIF admission/playback, composition,
hook retries, provider hit boundaries and gesture priority, deferred identity and
metadata checks, teardown, haptic counts, and native menu fallback. These are host
fixtures, not execution of UIKit's real gesture arbitration.

Build-2 local validation: 165 host tests run, 162 passed and three skipped (Apple
Foundation, the matching private Hermes runner, and the exact private donor).
All ten RN composer cases passed. Native dylib/framework contracts, both DEB
packages, the developer bundle, and the final unsigned IPA verification passed.
The documentation gate checked 68 Markdown files and 648 explicit references
with zero errors. No Hermes graft or RN library payload changed in this trial.

Build metadata is `3.1.0`, framework bundle `3.1.0.2`, and diagnostic label
`3.1.0-build.2`. Twitch's donor version is unchanged. The app-icon trial remains
included; its build-1 device observation is recorded in
[App-icon trial](APP_ICON_TRIAL.md).

Device checks for this build:

- Hold static, wide, animated, repeated, and newly downloaded provider emotes in
  the RN input; verify the provider sheet, preview, labels, actions, and one haptic.
- Hold ordinary text, whitespace, and a native Twitch emote; verify normal caret,
  selection, scrolling, and native menus.
- Tap, move, delete/retype an emote, switch chats, dismiss/reopen the keyboard,
  background/foreground, and exercise prediction/IME composition.
- Confirm the draft and cursor survive sheet dismissal, then send the draft.
- Compare the legacy composer and RN transcript/library hold behavior.

Record iOS/device, signing route, renderer, donor/build, cold/warm catalog state,
visible results, and diagnostics. Host and package checks do not establish device
interaction. Public feature and release documents are reconciled at feature
freeze under [Documentation maintenance](DOCUMENTATION.md).
