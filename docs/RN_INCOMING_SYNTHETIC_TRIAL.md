# Twitch 31.5 RN incoming synthetic-ID trial — build 55

## Subsequent device results

User reports B/C confirmed the observed incoming 7TV static and animated images
were correct, with animation continuing after offscreen/back scrolling. Report C
recorded 80 rewritten frames, 87 matched words and 114 successful provider image
responses, with no reported transport/empty/cancellation failures. Those are
aggregate counts, not 114 unique visible emotes. Wide images still occupied
square boxes. The original build-55 implementation/validation record below is
preserved; the next incoming-only width experiment is
[build 56](RN_INCOMING_WIDTH_TRIAL.md).

## Scope and stopping point

First functional experiment on `compat/twitch-31.5`, based on build 50's clean
source at `3fbfa44`. Builds 51–54 and final findings remain on
`diagnostic/rn-chat-boundary` (`040a0d1`). The legacy baseline remains archived.
No forensic probe implementation is imported or enabled in this build.

The first acceptance case is **an incoming square static provider emote**.
There is no iOS device in this environment: passing host harnesses and package
checks do not establish that Twitch's RN parser executed, that its image loader
decoded the provider asset, or that the image was visibly displayed.

Donor: Twitch 31.5 (`262752111271985979`), SHA256
`718762b71095c11754b1f58ad01fb580852414e6d7f468fbb2236b7c2419e641`.
The earlier passive reports identified its embedded Hermes-98 body as
27,786,480 bytes, FNV64 `3c748f1f3e33577c`.

## Implementation

`TASEmotes.c` now shares its existing IRC frame transform between the old
NSURLSession message wrapper and RN's direct NSString callback. A new hook
replaces only the concrete `RCTWebSocketModule` implementation of
`webSocket:didReceiveMessage:`. It calls the saved original once with either a
changed NSString or the exact original message object. The original RN delegate
still creates/emits `websocketMessage`; no second event or JS injection is used.

The receive route is admitted only for an `SRWebSocket` with an NSURL whose
host is exactly `irc-ws.chat.twitch.tv` and scheme is `ws` or `wss`. Non-chat
sockets, NSData/binary or nil messages, disabled preferences, incompatible ABI,
and unchanged frames keep their original behavior. Hooks retry through the
existing application-launch/settings bootstrap, and install only once.

Read-only metadata inspection of this exact donor reconfirmed:

| Method | Encoding |
|---|---|
| `RCTWebSocketModule.webSocket:didReceiveMessage:` | `v32@0:8@16@24` |
| `SRWebSocket.url` | `@16@0:8` |

Runtime installation checks those encodings (or equivalent compact object-only
encodings), requires the receive method to belong directly to the concrete
class, and does not change an inherited method on a parent class.

The reused matcher appends synthetic-ID groups to real IRC `emotes=` metadata,
using Unicode code-point positions and inclusive ends. It preserves message
body bytes, existing native ranges and unrelated tags. Native overlaps win.
Normal ROOMSTATE/PRIVMSG room discovery can start asynchronous provider fetches;
there is no synchronous network wait or message replay after loading.
Consequently, messages that arrive before their provider registry loads remain
literal text. Later incoming messages use the loaded registry.

Small parser guards needed for the receive adapter:

- Parse command/tag boundaries, not command-looking body text or similar tag
  names. Refuse duplicate or oversized native `emotes` tags rather than losing
  overlap protection.
- Match the actual room ID, never the last/background room's registry. Messages
  with a foreign, invalid or duplicate shared-chat `source-room-id` pass through.
- Bound input to 65,536 UTF-8 bytes, refuse embedded NUL/encoding failures, and
  preserve CRLF/multiline frames, including control lines before chat.
- If allocation or cumulative expansion fails, deliver the entire original
  frame, not a partially rewritten batch. Re-delivery is idempotent because
  already-tagged provider ranges receive native-overlap protection.

The expected downstream chain remains:

1. RN delegate receives rewritten IRC metadata.
2. Twitch's unchanged parser creates ID-bearing ranges and emote parts.
3. Unchanged `EmotePart` constructs `/emoticons/v2/<synthetic-id>/...`.
4. Existing Streamside request redirection maps that ID to its provider URL.
5. Twitch's RN image loader decodes and displays the asset.

Only the production delegate/rewrite and registry/request mapping are exercised
by the host harness. The JS parser and native RN image loader are **not** mocked
and then counted as live successes; those downstream steps require the device.

## Explicit exclusions

No send hook, local echo investigation, composer value/map/template mutation,
provider catalog injection, picker overhaul, tap-detail integration, or paragraph
attachment mutation is added. The existing legacy components remain unchanged.
No Hermes body, React framework or native emote-input framework is patched.

RN's normal inline boxes remain 24×24 (56×56 enlarged). A wide asset may fit
inside a square box; that is not proportional width support. The matcher still
recognizes ordinary provider entries, so wide/animated assets may reach the
loader, but their geometry and animation are not acceptance claims for this
experiment. The Fabric child-measurement/reservation seam identified in the
diagnostic findings remains the later geometry work.

## Device test — incoming only

1. Sign/install the unsigned build 55 IPA. Enable third-party emotes in
   Profile → Settings → Streamside and fully terminate/relaunch Twitch.
   Enable normal diagnostic logging for this test.
2. Capture report A before opening chat. Confirm the label is
   `3.0.0-build.55` and the RN incoming synthetic-ID hook is installed.
3. Open a channel with a known square static provider emote. Allow its provider
   fetches to finish. Receive that code from another account or an ordinary
   incoming message; do not use this account's sending/local echo as the test.
4. Confirm the literal code becomes the **correct image**, alongside native
   Twitch emotes and plain text. Capture report B after the relevant message.
   Record whether the image was visible, blank, wrong, or still literal text.
5. Scroll away/back and change channels. Verify native emotes/plain text and
   non-chat traffic still behave normally. Do not interpret square-box wide
   images as a completed width implementation.

Normal sanitized reports add:

- `RN incoming synthetic-ID hook` — installed/missing, not proof of invocation.
- `RN receive callbacks/IRC/rewritten/non-text` — aggregate callback categories;
  rewritten counts show replacement frames handed to the original delegate.
- `IRC frames refused (size/encoding/allocation budget)` — safe fallback counts.
- Existing matched words/native overlaps, registry/fetch counts, image mapping,
  provider protocol requests and response MIME/error counts remain available.

These counters contain no retained chat text, room/user IDs, synthetic IDs,
URLs, body ranges, raw pointers, image bytes or payloads. They are cumulative
from one launch. Image requests/responses are aggregate and cannot alone prove
that a specific image was decoded or displayed; the visible device observation
is required. No new live image/paragraph correlation observer is added.

If rewriting rises but no provider image requests occur, investigate the active
RN request interception boundary next. If requests succeed but no image appears,
investigate decode/display next. Do not jump to catalog or local echo changes.

## Host validation

`tests/test_rn_incoming.py` executes production code with a minimal Foundation
dispatch fixture under AddressSanitizer/UndefinedBehaviorSanitizer. Coverage:
native range precedence, exact tag/command parsing, Unicode/punctuation/repeated
matches, multiple IRC rows, unchanged object identity, exactly-once original
delivery, repeated delivery, room/global scope, shared-chat pass-through,
non-chat host/scheme/binary/nil/disabled gates, embedded NUL and size limits,
oversized native metadata, whole-frame expansion fallback, the old NSURLSession
wrapper contract, synthetic-ID provider URL mapping, exact hook ABI, concrete
method ownership, and retry idempotence.

Full compatibility host suite: **62 tests passed**, none skipped, using
`EMOTE_DIAGNOSTIC=0 ZIG=/path/to/zig-0.14.0/zig make verify test`.
Both framework/dylib artifact checks, Python compilation and `git diff --check`
passed. This is not the separate diagnostic
branch's 64-test suite. Build 55 does not import those forensic tests/tools.

## Package verification

`patch_ipa.py` and `verify_ipa.py` passed using the exact donor above and the
verified normal-build framework. Report label: `3.0.0-build.55`; framework bundle
version: `3.0.0.55`. Output:
`Twitch-31.5-Streamside-build55-incoming-synthetic-unsigned.ipa`.

- 4,251 donor entries are byte-identical; no donor entry is removed. Only the
  main executable's injection load header/padding and app display-name plist
  change. The framework binary and its plist are the only two added entries.
- All 15 RN/Hermes-related donor entries selected by React/native-input
  framework or Hermes/bundle paths are byte-identical, as is `Assets.car`.
- Normal framework includes the new receive status and no RN forensic probe,
  paragraph observer, Inspect Emote or rolling-playback markers.
- IPA: 191,814,211 bytes; SHA256
  `4bd3c2bc23aedbab163243fa722fa78688cad31f85721dbfcce5f7828b339a8d`.
- Framework SHA256:
  `b004d7604989206b529ef9168d1b71fe911e8edd7bae355722262f4fe859d7dd`.

The output is unsigned. Sign with the usual sideloading tool before installing.
No release/tag is created. Device rendering remains pending even though the
host, donor-ABI and artifact checks passed.
