# Chat rendering

Provider emotes enter Twitch through its existing emote representations. Streamside preserves message text, native ranges, and the surrounding message objects, then lets Twitch construct the displayed images.

RN and legacy UIKit have different entry points and geometry mechanisms. Their shared parts are provider matching, synthetic image routing, and metadata ownership.

## Incoming RN messages

The concrete `RCTWebSocketModule.webSocket:didReceiveMessage:` adapter in [TASEmotes.c](../../../src/TASEmotes.c) admits the inspected Objective-C ABI and an `SRWebSocket` whose URL host is `irc-ws.chat.twitch.tv`. Other socket hosts and unsupported values retain their original delivery.

`rewrite_text_impl()` handles bounded text frames and preserves unchanged values. `rewrite_line_mode()` admits actual IRC header tags, resolves the message's own room, and appends provider ranges to `emotes=`.

The incoming adapter observes `ROOMSTATE` as well as `PRIVMSG` to initiate catalog loading. A room is not inferred from a global “current stream” UI assumption.

### Range convention

IRC ranges use **Unicode code-point positions with inclusive ends**. UIKit editor ranges are UTF-16 and are not interchangeable.

For a word after an emoji, its UTF-8 byte offset, UTF-16 position, and IRC code-point position can differ. `codepoints()` counts the code-point span used by the IRC representation; existing native ranges are compared in that same coordinate system.

Matching tries an exact full token before trimming supported boundary punctuation. It computes the matched start/end after that trim and rejects overlap with native Twitch ranges. The actual body bytes remain unchanged.

### Admission and refusal

The receive path leaves unsupported frames untouched. Important refusals include duplicate `emotes=` tags, oversized native range metadata, duplicate/invalid source-room tags, unknown room syntax, and a foreign `source-room-id`.

The additions buffer is bounded. Matching stops when no additional encoded range fits; it does not write an incomplete range. Allocation failure retains the original line. Existing tags and native ranges are copied, and the saved delegate receives one complete delivered value rather than an extra synthetic message.

Registry loading is asynchronous. A message received before its definitions arrive remains literal; the adapter does not queue or replay old chat. Counters distinguish receive callbacks, rewrites, matches, native overlaps, and refusal.

## RN proportional identity

Ordinary stable image IDs are described in [Providers](PROVIDERS.md). RN chat uses a separate width-bearing alias:

```text
860000000000000 <= alias < 861000000000000
alias = base + (ordinaryID % 100000000) * 10000 + round(clamp(aspect, .125, 5) * 1000)
```

The low four digits encode thousandths of the admitted ratio. Registry admission still checks collision and asset ownership. A numerically plausible alias alone cannot resolve a provider image.

The ratio freezes when the alias is first admitted. Unknown dimensions can therefore produce a square alias; later dimension discovery does not silently change what that existing cached identity means. This representation does not implement zero-width overlay composition.

## Width before Fabric measurement

Twitch's `EmotePart` creates an inline wrapper and its image. Widening only the bitmap leaves paragraph reservation/wrapping square. The guarded patch in [TASRNWidthPatch.h](../../../src/TASRNWidthPatch.h) updates both styles before Fabric measures the inline child.

Equivalent explanatory logic is:

```js
const ratio = (Number(emoteId) % 10000) / 1000;
const width = (gigantified ? 56 : 24) * ratio;
wrapperStyle = [originalWrapperStyle, {width}];
imageStyle = [originalImageStyle, {width}];
```

Only admitted width aliases receive the override. Native, unknown, and old ordinary IDs retain their original style objects. Both insertions occur after memoized style selection, including reused renders. Original height, baseline styling, source selection, and decoder behavior remain in place.

The original inspected function is Hermes function 19127. The patch appends its adjusted body and redirects its function header, preserving original unrelated offsets and functions. Original branch structure is verified rather than guessed from a marketing version.

The native paragraph attachment research found reconstructed inline-child placeholders. Changing their bounds after layout would not reliably change RN's measured emote subtree. That historical discovery is in [RN native presentation seam](../../archive/investigations/RN_NATIVE_PRESENTATION_SEAM.md).

## Source ownership and patch admission

`rn_source_data()` first calls the original `RCTSource.data`. The complete original body is 27,786,480 bytes, Hermes version 98, SHA-256:

```text
422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b
```

The runtime width gate also checks the expected SHA-1 footer, recomputes it over the body, and validates the original small/large function headers. It creates new bytes and an associated `NSData`; neither the donor file nor the caller's original data is mutated.

The source instance caches its checked result. Failure preserves original source data. Further stages have their own structural admissions; successful width installation does not by itself prove local-message, composer, details, or picker installation.

## Ordinary own-message display

Own messages do not traverse the incoming rewrite in the same way. The retained adapter targets `LibraryTmiClient`'s completed ordinary-chat display line in function 34307, after translation and client-nonce handling and before the original `emitLine`.

The original line, body, identity, and native range objects remain intact. The patch calls the synchronous provider-range bridge with body, normalized explicit channel, and native ranges. A nonempty result is concatenated to the native array. The send payload, reconciliation, and original emission semantics are unchanged.

`rn_local_ranges()` validates bounded strings and at most 128 native ranges. Start/end values must be integral code-point positions within the completed body. Native objects are not reconstructed; only their positions protect ownership.

A private in-memory IRC carrier reuses the matcher. It is not transmitted or logged. Unknown/ambiguous room scope, unsafe input, or missing definitions returns no additions. This synchronous operation does no provider fetch, UIKit work, or sending.

The separate action-message handler, function 34310, is not patched. Ordinary own-message success does not establish provider rendering in `/me`.

### Call-frame correction

Builds 57/58 patched the separate `TmiClient.buildLocalEcho` path and recorded no local callbacks on the tested sends. Build 59 reached the real event path but hid messages before native preview entry.

The host instruction mock had missed Hermes' sequential outgoing `Call4` writes. Frame 18 staged arguments over a live callee register before reading it. Build 60 raised the frame to 21 so outgoing slots no longer clobber live locals, and added an exception handler around only provider preview work.

Missing exports, null results, or exceptions in that added work resume original `emitLine`. The handler does not swallow Twitch's original send, translation, or emission errors. [The local-display trial](../../archive/experiments/RN_LOCAL_ECHO_TRIAL.md) preserves the failure sequence and independent compiler/disassembly evidence.

## Legacy UIKit own-message presentation

[TASEmotePresentation.c](../../../src/TASEmotePresentation.c) enriches `currentChannelUnlockedSubscriberEmotesForMessageString:` on the inspected `ChatDataSource` and `ChatTranscriptView`. It does not replace `TWChatMessage`, its tokens, or `ChatMessageString`.

The adapter resolves live account/channel authority, including the `NSNumber` sender bridge. A direct data-source manager or an unambiguous weakly observed manager supplies the current user; cached account identity is not authoritative.

It refuses historical messages, foreign shared-chat messages, unsafe moderation subclasses, unexpected token arrays, missing authority, and native-code conflicts. Subscriber and follower definitions protect existing Twitch codes.

Provider codes are found using the inspected native matcher's literal-space boundaries. Constructed `TKChatEmote` definitions must retain the requested identifier/code, report `isRegex == false`, and use the admitted `assetType == 1`. That asset type comes from native call-site evidence; it is not an animation flag.

Up to 64 added definitions are passed back in a copied native array. Twitch performs its normal token/attachment construction. This is the retained build-50 legacy seam, not the RN own-message patch.

## Legacy proportional geometry and animation

[TASEmoteUI.c](../../../src/TASEmoteUI.c) identifies provider-owned presentation objects and coordinates TextKit spacing with image-layer frames. Correct reservation alone was insufficient when the separately displayed image stayed square. Native/foreign IDs retain their original geometry.

[TASEmoteGeometry.h](../../../src/TASEmoteGeometry.h) provides idempotent aspect handling. Repeated getter/setter calls must not multiply the width repeatedly. Very wide ratios use the supported capped box rather than fabricating overlay behavior.

Legacy provider `TWAnimatedImageLayer` recovery retains Twitch's decoder/playhead. A weak layer set and one one-second common-mode timer check active/visible/clipped state, repair an exhausted provider countdown, and invoke native animation-state reevaluation. The timer stops when no tracked provider layer is visible. Native layers are not reset or enrolled as provider recovery targets.

RN transcript animation remains Twitch's native image-decoding path. Composer animation is separately described in [Composer](COMPOSER.md).

## Tests and evidence limits

- [Incoming tests](../../../tests/test_rn_incoming.py): code-point ranges, punctuation, native overlap, refusal, and original-value preservation.
- [Width/local tests](../../../tests/test_rn_width.py): alias geometry, donor function metadata, sequential call-frame behavior, and exception fallback.
- [Legacy presentation tests](../../../tests/test_emote_presentation.py): current-account authority, constructor identity, native conflicts, and unsafe-message refusal.
- [Geometry tests](../../../tests/test_emote_geometry.py) and [UI tests](../../../tests/test_emote_ui.py): proportional reservation and provider-only presentation.
- [Donor verifier](../../../tools/verify_rn_width.py): exact bytecode structure and patch-chain checks.

Host fixtures establish transformations, ownership, and failure contracts. Donor checks establish bytecode admission. Device reports establish the separately recorded visible result on the tested configuration; none of these alone grants support for an unknown Twitch build.

[Feature map](README.md) · [Architecture](../../ARCHITECTURE.md) · [History](../../HISTORY.md)
