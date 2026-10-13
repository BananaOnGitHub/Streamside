# 3.1.0 build 3 — RN composer cursor requests

Branch: `dev/3.1.0`; source baseline `16188d5`. Target: Twitch 31.5
(`262752111271985979`). Continued typing around an emote token can leave the
cursor inside newer text. This trial addresses two stale selection-request paths;
device confirmation and broader typing-performance investigation remain pending.

## Donor evidence

The native input framework extracted from the verified build-2 IPA is 315,728
bytes, SHA-256 `fdcb23b068a5c3024faef76c1fcc82d3e5e5a7592fd7755cc46740d0fc41335f`.
Read-only inspection used the historical
[presentation reader](https://github.com/BananaOnGitHub/Streamside/blob/040a0d1/tools/inspect_rn_presentation.py)
and its metadata helper, with Capstone 5.0.7. Addresses are specific to this binary.

- `setSelection:` (`0x77c8`) enters the Swift property observer at `0x7840`.
  A nonnil request increments `selectionGeneration`, then queues a weak-owner
  main-queue closure carrying that generation and the requested plain offsets.
- The closure (`0x7c90`) checks only the captured generation before calling
  `applySelection` (`0x7d40`) against the current attributed text. It does not
  check the draft the request originally described.
- The nil property path (`0x7a40`) increments the generation without applying a
  selection or rewriting text. The inspected edit/change paths do not invalidate
  that generation when more text is entered.
- Native tokenization maps between displayed attachment positions and expanded
  UTF-16 positions. That mapping remains under Twitch's control.

Consequently, a queued request can remain valid after newer typing. A controlled
host fixture reproduced the old requested position replacing the newer cursor
before the guard was added. This is evidence for a concrete race, not proof that
it explains every reported displacement or establishes typing latency.

## Scoped correction

[TASRNComposerUI.c](../../src/TASRNComposerUI.c) hooks the exact RN owner's
`textView:shouldChangeTextInRange:replacementText:` method. The original validator
runs first. Only an accepted edit in the admitted editor invalidates an existing
selection prop through the original nil setter, before UIKit performs the edit.
Vetoed edits retain their selection request. Missing ABIs, disabled emotes,
foreign editors, and background callbacks preserve the original path.

The `setSelection:` hook also checks Streamside suggestion requests, which
[ProviderEmoteStrip.js](../../src/rn/ProviderEmoteStrip.js) already labels with
their expected `text`. A mismatched live draft, or active marked text, converts
that request to nil. Valid requests and native requests without that context
still call the original setter. Reading `currentPlainText` requires the existing
Swift String bridge, the exact owner class, a verified 16-byte field span before
`imageCache`, and instance bounds; unavailable layouts retain native behavior.

Both selection getter/setter and the edit callback require their full Objective-C
type encodings. No private field is written. No draft, attachment, tokenizer,
outgoing message, Hermes payload, or current UIKit selection is rewritten by the
guard. There is no typing debounce. Diagnostics report only aggregate invalidated
props and refused stale requests, plus hook availability.

## Validation and device checks

[RN composer tests](../../tests/test_rn_composer_ui.py) exercise production hooks
with sanitizer-backed controlled ABI adapters. The queued-selection fixture models
the inspected donor closure; it does not execute UIKit or the donor's Swift code.
New regressions cover accepted versus vetoed edits, late versus matching drafts,
native requests, marked text, field/bridge refusal, disabled/foreign/background
fallback, full ABI admission, and retry/idempotence.

Build-3 local checks: 168 host tests run, 165 passed and three skipped (Apple
Foundation, the matching private Hermes runner, and the exact private donor).
All 13 RN composer cases passed. The three cursor-related method encodings were
also checked against the inspected native donor metadata. Native artifact
contracts, both DEB packages, the developer bundle, and the unsigned IPA passed
verification. Documentation validation found zero errors across 70 Markdown
files and 663 explicit references. These results do not establish device behavior
or a typing-performance improvement.

Device acceptance should include rapid typing after manual recognition and
suggestion insertion, repeated codes, emoji before tokens, edits in the middle of
a draft, deliberate selection movement, paste/delete/undo, prediction and IME,
and send/clear/channel transitions. Verify the cursor stays at the intended edit
position, not necessarily the end. Compare native Twitch and provider emotes.
The icon and hold-popup trials remain included.

Record donor/build, device/iOS/signing route, interaction results, and sanitized
cursor counters. Finalize maintained feature documentation at feature freeze
under [Documentation maintenance](../development/DOCUMENTATION.md).
