# Twitch 31.5 local sent-message preview — build 58

## Objective and seam

Render third-party codes in this account's local chat preview, reusing build 56's
device-confirmed incoming images and proportional layout. Catalog, picker and
composer preview remain deferred. The build-57 device trial did not render the user's emote: registration and
patching were active, but all four local callback counters were zero. That rules
out a refusal inside the matcher. It does not distinguish an unused local
function from a missing proxy/module/method. Build 58 addresses the incomplete
bridge lookup; live validation remains pending.

Exact donor identity is unchanged from the width trial: Twitch 31.5 build
262752111271985979; original Hermes-98 body 27,786,480 bytes, SHA-256
`422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b`.

Static donor trace:

| Function | Role |
| --- | --- |
| 34208, `0x017e132d` | Sends the original body via raw IRC or onSendChatMessage; then separately builds/parses a local echo and calls emitChatMessage/emitLine |
| 34222, `0x017e1ec2` | buildLocalEcho: constructs identity, nonce, reply and native-emote tags plus the final preview string; anonymous/missing-login gates return null |
| 34253 | Normalizes the client channel to lowercase and removes a leading `#` |
| 19127 | Shared EmotePart, already patched for proportional aliases |

Patch only the completed preview return, before its existing parse/emission.
Send functions, payload creation, nonce/error handling, line/message emissions
and native emote tag construction remain byte-identical. No additional send or
echo is created. The original local echo sequencing and reconciliation remain
Twitch's responsibility; their live behavior still needs testing.

## Bridge and matching

A separate NSObject class, TASRNLocalEchoModule, adopts RCTBridgeModule and uses
the standard RCTRegisterModule/RCTMethodInfo registration/export contract.
The donor exports RCTRegisterModule and contains legacy TurboModule interop.
Registration availability is distinct from proof that JS can resolve/call it.
There is no modification of existing native modules or C++ runtime storage.

For constant-pool preservation, the module and exported method both use the
existing string `buildLocalEcho`; the Objective-C selector is renderLocalEcho:.
Build 57's 45-byte block looked only at global.nativeModuleProxy. The donor's
NativeModules factory (function 20, Metro module 16) selects that proxy when
available and otherwise builds modules from __fbBatchedBridgeConfig. Build 58
uses the existing global.__r loader to require module 16, reads its default
export, then resolves buildLocalEcho and calls it with the completed preview.
The loader's global installation, exact module registration and both factory
routes were traced in the donor; the read-only verifier checks the module ID,
factory and reused constants. Missing loader/exports/module/method preserves
the original preview. The synchronous callback
does bounded in-memory matching only, with no network, dispatch or UIKit work.

The callback requires an NSString, a single bounded UTF-8 PRIVMSG preview, a
numeric `id=local-echo-...` tag, and exactly one live room associated with the
preview's explicit channel. It never borrows the most recently received room.
ROOMSTATE now associates a channel even when no incoming PRIVMSG has arrived.
Unknown/ambiguous room scope preserves the original preview.

Reuse the shared code-point/punctuation matcher and native-range overlap rules.
Add a temporary internal room tag, match, then remove that tag before returning.
Only emote metadata changes: body, identity, nonce, reply and native tags stay
unchanged. Aliases and their existing redirects/history/width freeze are shared
with reception. Incoming frame counters exclude this route; general word/alias
counters can include both routes.

Disabled/unpatched, non-text, oversized, embedded-NUL, multi-line/control/action
previews, foreign room tags and malformed scope keep the original object. `/me`
is not an acceptance case for this experiment. Missing provider definitions at
send time remain text; there is no later replay or retrospective repair.

## Admission and static verification

The source getter first admits the exact original full-body SHA-1 and applies
the unchanged width patch. Local patching requires successful native module
registration plus the original local function's exact small header. A failed
second stage keeps the working width-only body. Failed source admission keeps
the original source data. All changes are in memory; disk bundle unchanged.

The local function grows 684 → 757 bytes and retains its original copy. Existing
dead Value registers r4–r7 carry the guarded bridge call; no frame, register-bank,
cache, string-pool, function index, exception or debug layout changes. Relocate
only the two anonymous/login branches to the original null return. All 15 local
and 34 width-function original branch destinations verify independently.
All other function headers and original-body bytes are preserved except file
length and the two target headers (12 original-body bytes differ).

The independent Hermes-98 compiler disassembles the complete patched body.
This is container/instruction verification, not Hermes execution or a live
NativeModules/Fabric test. Host harnesses exercise production matching,
registration/export ABI and export-discovery counting, availability/idempotence,
object identity, preview
metadata/Unicode/native ownership, room switches and quiet-room association,
alias redirects, patch refusal/immutability and emitted guarded-call semantics.

```sh
ZIG=/path/to/zig EMOTE_DIAGNOSTIC=0 make verify test
PYTHONPATH=/path/to/hermes-dec ZIG=/path/to/zig \
  python3 tools/verify_rn_width.py /path/to/twitch-31.5.ipa \
  --local --hermesc /path/to/hermesc
```

## Device reports

1. Sign/install build 58, enable third-party emotes and diagnostics, fully relaunch.
   Enter a channel and allow provider definitions to load. Capture A: build label
   58, width active, `RN local preview module/patch: registered/active`.
2. Send a known provider code manually, then a wide animated code alongside text
   and a native Twitch emote. Capture screenshot/B. Expect one own message with
   correct images, normal height, proportional width and unchanged surrounding
   text. Expect local calls/rewritten to rise; refusals/scope misses ideally zero.
   Native-only and plain-text sends should remain ordinary single messages.
3. Scroll away/back, switch channels and repeat with a channel-specific code;
   optionally test repeated codes, emoji before a code and a reply. Capture C.
   Verify no wrong-room images, duplication, vanished preview, delayed correction
   or animation/wrapping regression; compare the actual sent text independently
   if another client is available.

New logs/counters contain only registration/patch state and aggregate export
discoveries/local calls/rewrites/refusals/scope misses. Export discoveries count
React Native asking for our method metadata, separately from C registration.
A nonzero value shows method discovery; it does not prove a JS method call. No text, identities, channels, room IDs,
URLs, source bytes, image bytes or pointers are stored. A registered/active
report with zero calls after normal sends indicates the JS bridge/path is still
unproven; a rewrite count alone does not prove displayed geometry or delivery.

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
