# 3.1.0 build 3 — RN composer cursor requests

Branch: `dev/3.1.0`; source baseline `16188d5`. Target: Twitch 31.5
(`262752111271985979`). Continued typing around an emote token can leave the
cursor inside newer text. This trial addresses two stale selection-request paths;
Device confirmation and broader typing-performance investigation were pending
at build preparation; subsequent feedback is recorded below.

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

## Build-3 device follow-up

Typing in the RN composer was reported to feel much faster with build 3 than
with the preceding build. The reported cursor jump during continued typing
around emote tokens was also confirmed no longer occurring. These are on-device
results for the exercised typing case, not a timed benchmark or a measured
latency reduction. The tested implementation is
`2c166bc`; the unsigned build-3 IPA has SHA-256
`4697c62d006c7328e04bb2c01b9f486c98e622e7afec433624564de4d723e6c1`.

The full interaction matrix, device/iOS/signing configuration, and cursor
counters were not recorded. Keep those remaining checks separate from the
confirmed resolution of the reported cursor jump and improvement in perceived
typing responsiveness.

Device acceptance should include rapid typing after manual recognition and
suggestion insertion, repeated codes, emoji before tokens, edits in the middle of
a draft, deliberate selection movement, paste/delete/undo, prediction and IME,
and send/clear/channel transitions. Verify the cursor stays at the intended edit
position, not necessarily the end. Compare native Twitch and provider emotes.
The icon and hold-popup trials remain included.

Record donor/build, device/iOS/signing route, interaction results, and sanitized
cursor counters. Finalize maintained feature documentation at feature freeze
under [Documentation maintenance](../development/DOCUMENTATION.md).

## Build-6 follow-up: late native requests on 31.6

Source baseline: `f3121d5`; Twitch 31.6 (`262821841498166537`). Build 5
was reported to run successfully, but continued typing after an emote becomes
an image can again displace the cursor. The build-3 confirmation on 31.5 is
preserved above; it does not establish this interaction on 31.6.

The native guard was not removed or changed by the port. Its accepted-edit
invalidation only cancels a selection that has already reached the native
owner. A request arriving afterward bypasses that cancellation. The second
guard checks a request's expected draft, but only Streamside's explicit
suggestion requests previously supplied it. Twitch's native autocomplete
returns `forcedSelection` objects containing just `start` and `end`.

Donor inspection resolves 31.6 `useAutocomplete` to function 21822. At `0x210`
its automatic draft-reconciliation branch constructs bare offsets from the
draft's UTF-16 length; the ordinary change callback 38293 clears forced
selection. Native input function 18502 forwards the selection object intact
at `0x2d0`. The corresponding automatic-offset branch also exists in 31.5
function 21416. This is an uncovered ordering case, not evidence that 31.6
introduced that algorithm or proof of the precise device event sequence.

The [autocomplete adapter](../../src/rn/ProviderEmoteStrip.js) now attaches the
draft from a native selection request's first observation. A weak-key cache
keeps that same request identity and original draft across later renders; an
old request is never relabeled with newer text. The donor object is not mutated,
and the existing native draft guard can reject late offsets once typing has
advanced. Other callback identities and command/mention matches remain native.
Off mode and disabled emotes retain the original requests. Requests outside
this adapter still use the existing native fallback.

No new React hooks, Swift-field writes, debounce, forced-end behavior, draft
rewrites, tokenizer replacement, or UIKit-selection mapping were added.
Current noncollapsed/middle selections retain their requested offsets.

### Regression coverage

The new [strip test](../../tests/test_rn_strip.py) first failed against build-5
source because a native request had no draft tag. It covers stable identity,
reused requests after newer text, fresh requests, immutable donor objects,
empty drafts, Unicode UTF-16 positions, noncollapsed selection, and off/disabled
fallback. The [native host fixture](../../tests/test_rn_composer_ui.py) models an
edit with no outstanding selection, followed by a late request: bare offsets
move the caret into newer text, whereas the tagged request is refused. It also
checks that a current request can still intentionally select the middle.

These controlled fixtures identify a concrete gap and its correction; they do
not execute UIKit/Fabric or establish that every reported cursor displacement
has the same cause. Build-6 device acceptance remains pending, particularly
rapid continued typing after recognition, deliberate middle edits, suggestion
insertion, prediction/IME, and send/clear/channel transitions.

### Build-6 validation and artifact

- Full host suite: 173 tests run, 172 pass, one Apple Foundation integration
  test skipped on Linux. The private exact-donor and matching Hermes cases
  execute rather than skip. All 17 native-input cases pass.
- The [compiled runtime fixture](../../tests/fixtures/snapshot_exercise.js)
  exercises the shipped request-tagging bytecode: original draft, reused-request
  identity after newer text, immutable donor object, callback identity, and a
  fresh current request. The required runtime gate also passes donor settings,
  32 bounded snapshots, and all 7,344 virtualization scenarios.
- Full graft verification passes deterministic regeneration, the donor's bare
  offset/selection forwarding bindings, all 48,996 predecessor functions,
  original constants/handlers/debug data, and independent Hermes-98 disassembly.
  The strip remains 131 functions; its owned payload grows from 28,492 to
  28,684 bytes. The donor fingerprint and predecessor admission are unchanged.
- Native artifact contracts and both DEB archives pass. The unsigned IPA
  passes packaging checks and a separate verifier. Documentation validation
  checks 72 Markdown files and 702 explicit references with zero errors.

Build-6 framework binary SHA-256:
`20875ea7e1e56af6ee0206ad79d7242ff6f03d4066458cfb59ce6cf7784b5ded`.
Unsigned artifact: `Twitch_31.6_Streamside_3.1.0-build.6_unsigned.ipa`,
194,477,541 bytes, SHA-256
`c9878fa8a888ce958fb7ab3b37915114859c864c1c9e030a69524873afcfa332`.
The Hermes compiler and snapshot runner are rebuilt from the same pinned source
and have the same hashes recorded for [build 5](TWITCH_31_6_COMPATIBILITY.md#build-5-hermes-port).
These results establish host/bytecode/package validation, not a completed
on-device cursor fix or a published compatibility claim.
