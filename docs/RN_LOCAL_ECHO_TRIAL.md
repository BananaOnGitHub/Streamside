# Twitch 31.5 local sent-message display — build 60

## Device evidence and corrected seam

Build 59 recorded one export discovery but zero native preview calls. The user
reported that sent messages disappeared entirely, after sending a static square
7TV code. This is a regression, not evidence of successful local rendering.
The host instruction mock missed Hermes' sequential outgoing-frame writes.
In donor frame 18, Call4 writes this/r7 to r10, body to r9, channel to r8, and
native ranges to r7. Its callee is still read from r8 AFTER those writes, so
the channel string replaces the callable. The resulting TypeError precedes
native entry and the original emitLine. Frame 21 isolates all outgoing writes
in r10..r20. A catch around only the preview resumes the original emitLine;
it does not catch Twitch's send/translation/emission errors.

The build-58 test sent one square static provider code. Module registration and
patching were active, but export discoveries, local calls, rewrites, refusals and
scope misses were all zero. Incoming matching and provider images continued to
work. Build 57 showed the same absence of local callbacks. This demonstrates
that neither attempt reached the callback; it does not independently establish
whether native-module discovery works on device.

The donor contains two chat clients. The preceding patches targeted TmiClient's
buildLocalEcho return. A separate connection factory constructs LibraryTmiClient,
whose inner TMIClient emits ordinary chat events, including local own messages. Build
59 moves the local patch to that event's line, before its existing emitLine.
Build 59's export discovery supports reaching module lookup on device, but
successful native entry and local rendering remain unverified.

| Function | Role |
| --- | --- |
| 34222 | Separate TmiClient buildLocalEcho; no longer patched |
| 34253 | LibraryTmiClient constructor and normalized channel |
| 34307, offset 25052014 | onChatEvent: emitMessage, translateChatMessage, preserve clientNonce, emitLine |
| 34310 | Separate onActionEvent handler; unchanged |
| 34311 | translateChatMessage: creates display line and native emotes array |
| 34348 | emoteRangesFromUser: native objects contain id, start, end |
| 19127 | Shared EmotePart: unchanged proportional width patch |
| 20 / Metro module 16 | NativeModules loader supporting proxy and classic bridge config |

Exact donor: Twitch 31.5 build 262752111271985979. Original Hermes-98 body:
27,786,480 bytes; SHA-256
`422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b`.

## Display-only adaptation

The injection runs in onChatEvent at the nonce-handling join, after the completed
body and native ranges exist. It gates on event.sentByCurrentUser and refuses sourceRoomID lines.
Resolve global.__r(16).default.buildLocalEcho, then call its synchronous method
with line.body, line.channel and line.emotes. Missing loader/module/method or a
null result or preview exception leaves the original line unchanged. On a match, concatenate only
provider additions to the original native array and assign line.emotes.

The line, identity, body, native range objects and client remain intact. Send
functions, payload creation, nonce/error handling, emitMessage, original emitLine
and reconciliation are preserved. No additional message, send or replay occurs.

A separate TASRNLocalEchoModule uses RCTBridgeModule/RCTRegisterModule. Its
existing module and JS method names remain buildLocalEcho to preserve the donor
constant pool. The selector is renderLocalBody:channel:nativeRanges:; exported
method metadata describes three arguments and a synchronous array return.
Registration, method discovery and actual calls are measured separately.

The adapter accepts bounded NSString body/channel and an NSArray of at most 128
native ranges. Validate each inclusive start/end as an integral code-point index
within the completed body. Native IDs and objects never round-trip through the
adapter; their positions only protect native ownership. A private in-memory IRC
carrier reuses the confirmed code-point/punctuation matcher and proportional
aliases, then returns provider-only {id, start, end} objects. The carrier contains
no real identity, nonce or reply metadata and is never transmitted or logged.

Match the explicit normalized channel to exactly one known room. Unknown,
ambiguous or invalid scope does not borrow the last received room or guess a
global-only scope. Missing provider definitions remain text. Oversized, malformed,
embedded-NUL and control/multiline inputs return null. Matching does no network,
UIKit, dispatch or send work. Existing provider redirects, alias history and
width freeze are reused. Incoming frame counters exclude this route; word/alias
counters include its matching work.

## Admission and verification

Source admission requires the original complete donor hash and the unchanged
width patch. Stage two requires native registration, the exact function-34307
small header and a valid width-patched footer. Failure keeps the width-only body.
Append a copy of the own-event callback: 121 → 288 bytes (164-byte injection plus
three bytes to widen its null-return branch). Append an aligned large header
and one exception-table entry; redirect only this callback's small header to
them. The exact full header is 40 bytes, with flags at byte 36. The provisional
hermes-dec 0.1.7 development-98 schema used 36 bytes/flags at 35; the verifier
corrects that analysis schema and cross-checks the compiler's actual metadata.
The protected interval covers only preview code and excludes Catch and
original emitLine. Original disk bundle is unchanged.

The null branch skips the injection. Both nonce-handling paths enter it. All
five original local branch targets
and all 34 width-function branch targets are checked. r4/r5 remain line/client;
r1–r3/r6–r9 are scratch Value registers at the join. Frame size is now 21;
number/non-pointer counts, caches and original function identity are retained.
Constant pools, original exception/debug data and all other function headers
stay intact. Only file length and the two target function headers change in
the original body (20 differing bytes).

Host tests cover square static and wide animated provider routes, Unicode,
repeated/punctuated codes, native overlap, malformed ranges, explicit room scope,
refusal/disabled states, native-object identity and bridge availability. The
exact-donor verifier checks all original instructions and branch targets;
Sequential frame-write tests reproduce build 59's pre-entry TypeError, then
verify frame 21 and exception fallback at every preview lookup/call/write.
Hermes-98 independently compiles a comparable call/catch probe to confirm its
eleven outgoing Call4 slots and disassembles the full patched container. These checks
prove neither live module resolution nor device rendering.

```sh
ZIG=/path/to/zig EMOTE_DIAGNOSTIC=0 make verify test
PYTHONPATH=/path/to/hermes-dec ZIG=/path/to/zig \
  python3 tools/verify_rn_width.py /path/to/twitch-31.5.ipa \
  --local --hermesc /path/to/hermesc
```

## Device test

Sign/install build 60 and fully relaunch Twitch. First send ordinary text and
check that exactly one own message appears. Load a channel's definitions,
clear diagnostics, then manually send the same known square static code.
Capture its display and the post-send report. Local calls should now increase;
a matched code should increase rewritten and request its provider image. Export
discoveries may occur at startup, before the log is cleared.

If square rendering works, test text plus a native emote and wide animated code,
emoji before a code, repeated codes, a reply, scrolling and a channel switch.
Check for one message, preserved text/native images, correct width/animation and
correct channel definitions. Compare sent text from another client if available.
Do not infer display success from a rewrite counter alone. The separate /me
handler is unchanged; action-message provider rendering stays deferred.

Diagnostics store only aggregate module/patch state, discoveries, calls,
rewrites, refusals and scope misses. They never store chat text, real identities,
channel/room IDs, URLs, source/image bytes or pointers. Catalog/picker work stays
outside this experiment.

## Build 57 validation and unsigned package provenance

The following records the prior build, whose device trial failed above.

69 host tests passed, none skipped, with sanitizer-backed production harnesses.
Framework/dylib artifact guards, Python compilation and git diff checks passed.
The exact donor's combined patch and independent Hermes disassembly passed.

Unsigned package: `Twitch-31.5-Streamside-build57-local-emotes-unsigned.ipa`.
Size: 191,819,281 bytes. SHA-256:
`e99e7642886e26fbf4ee7e8018c63359622614d138a81bf3958cc8f6bd2e6bad`.
Framework SHA-256:
`1b30a37c137d9b0c2d095d9e7d296d37f9fb29f3211af77f732b173799b48435`.
patch_ipa/verify_ipa passed. 4,251 donor entries remain byte-identical, none
removed. Only the executable injection header/padding and display-name plist
change, plus the two new framework entries. The embedded bundle and React
framework remain byte-identical. Sign with the usual sideloading tool.

## Build 58 validation and unsigned package provenance

69 host tests passed, none skipped, including the no-nativeModuleProxy lookup
regression, missing-loader/module/method identity fallbacks, and export-discovery
counting. Framework/dylib artifact guards, Python compilation and git diff checks
passed. The exact donor combined patch, NativeModules module/factory/constants
verification, original branch checks and independent Hermes disassembly passed.
These checks do not establish live bridge resolution or own-message rendering.

Unsigned package: `Twitch-31.5-Streamside-build58-local-emotes-unsigned.ipa`.
Size: 191,819,420 bytes. SHA-256:
`cc96fa25ea272ac0bf00163e7424523dae5eb4e3b2cb6741e3cbc9b9bdc7190c`.
Framework SHA-256:
`a24c88d0ef442cf0733cd9c338ffcb3c2cbaf8b8a2adc62da8ad26b11b0876e7`.
patch_ipa/verify_ipa passed. 4,251 donor entries remain byte-identical, none
removed. Only the executable injection header/padding and display-name plist
change, plus the two new framework entries. Embedded JS and React framework
remain byte-identical. Sign with the usual sideloading tool, then fully relaunch.

## Build 59 validation and unsigned package provenance

70 host tests passed, none skipped, including the display-array adapter and
ordinary-chat own/scope gates. Framework/dylib guards, Python compilation and
git diff checks passed. Exact donor method-binding, all original branches and
instructions, NativeModules registration and Hermes-98 disassembly passed.
Its subsequent device report confirmed a regression: sent messages vanished;
one export discovery and zero native calls were recorded.

Unsigned package: `Twitch-31.5-Streamside-build59-local-emotes-unsigned.ipa`.
Size: 191,820,916 bytes. SHA-256:
`40351e6bb50cad4ded95cb069b6838a6c0402a4a5b8f8f678af4ad10ede380e3`.
Framework SHA-256:
`d952fe5677d12ac884d5e64add0952bcbf4ec572a6ff589e0c66381e12949afa`.
patch_ipa/verify_ipa passed. 4,251 donor entries remain byte-identical, none
removed. Only executable injection header/padding and display-name plist change,
plus the two framework entries. Embedded JS and React remain byte-identical.
Sign with the usual sideloading tool, then fully relaunch.

## Build 60 validation and unsigned package provenance

71 host tests passed, none skipped, including reproduction of the frame-18
pre-entry TypeError and fail-open checks for every preview lookup/call/write.
Framework/dylib artifact guards, Python compilation and git diff checks passed.
Exact donor method binding, all original instructions/branch targets and
unchanged exception/debug metadata were checked. The same Hermes-98 compiler
independently confirms eleven outgoing Call4 slots. Its disassembler recognizes
the patched callback's frame 21 and Catch table using the actual 40-byte header.
These checks do not prove live native-module invocation or local rendering.

Unsigned package: `Twitch-31.5-Streamside-build60-local-emotes-unsigned.ipa`.
Size: 191,821,011 bytes. SHA-256:
`37ef0a5d55277832b852184f10e88e0dcc3ca677ead752235d99ffe2ede310e1`.
Framework SHA-256:
`f7cb05f0c652554762b3e08bff925ab8440e6694c9b1e2293f35d18577c36aab`.
patch_ipa/verify_ipa passed. 4,251 donor entries remain byte-identical, none
removed. Only executable injection header/padding and display-name plist change,
plus the two framework entries. Embedded JS and React remain byte-identical.
Sign with the usual sideloading tool, then fully relaunch and test plain text
before the same static square provider code.
