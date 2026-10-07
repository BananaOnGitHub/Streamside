# Twitch 31.5 incoming RN proportional width — build 56

## Objective and scope

Build 55's observed incoming provider images are correct; animated examples
continue after scrolling (user reports B/C). The remaining reception problem is
the fixed square layout. This experiment changes **both the inline wrapper and
image width before Fabric measurement**, keeping their existing 24-point inline
or 56-point enlarged heights. No UIKit frame workaround, paragraph attachment
mutation, catalog, picker, sending/local echo, or animation hook is added.

The implementation is a narrow **in-memory Hermes component patch**, not a
native Fabric/C++ storage-offset hook. It patches only the incoming EmotePart
function and never changes the JS bundle or React/Hermes framework on disk.
Width is not yet verified on a device. This is an experimental compatibility
build, not a release/tag.

## Exact admission and fallback

The concrete `RCTSource.data` getter has the verified donor ABI `@16@0:8`.
Install only its own matching method, once, while the launch preference is on.
Each source's getter still calls its original once; a source-owned associated
NSData caches the successful copy. Disabled, incompatible, unrelated or failed
sources retain the original object. The original source URL is untouched.

The patch requires all of:

- Body length 27,786,480, Hermes magic/version 98, matching file length.
- Exact original small/large function headers for function 19127 (EmotePart).
- Expected footer SHA-1 `5f22119749242717f3788797cf50a77f0edc0715`, independently
  recomputed over the complete original body preceding the footer.
- Available platform `CC_SHA1`, successful allocation and successful new SHA-1.

Body SHA-256: `422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b`.
Donor IPA SHA-256:
`718762b71095c11754b1f58ad01fb580852414e6d7f468fbb2236b7c2419e641`.
Original body FNV64: `3c748f1f3e33577c` (earlier passive device evidence).

If admission fails, proportional aliases are not emitted: build-55 reception
and square boxes remain available. No approximate-version or guessed-ABI route
is used. A full relaunch is required, including after changing the preference.

## Style and image identity

The matcher emits proportional aliases **only through the confirmed RN IRC
receive route after successful source patching**. The legacy receive path keeps
its existing synthetic IDs. Alias namespace is `[860000000000000,
861000000000000)`; the low four digits encode round(aspect × 1000), limited to
125..5000. Eight stable hash-derived digits distinguish image identities.
All values stay exact in JavaScript's numeric representation.

Registry admission checks aliases against live/global/history image identities;
a collision keeps the original ID rather than mapping to another image. The
existing request redirect recognizes the precise new namespace and resolves
aliases only through the registry. Both original and alias IDs retain the
existing bounded eviction grace. Dimensions freeze when an alias is first used,
so its cached CDN URL never changes image identity.

The inserted instructions at original bytecode boundaries `0xd0` and `0x238`
apply the equivalent of:

```js
// Explanatory reconstruction; not injected source text.
if (idNumber >= 860000000000000 && idNumber < 861000000000000) {
  const ratio = idNumber % 10000;
  if (ratio >= 125 && ratio <= 5000) {
    style = [style, {width: (gigantified ? 56 : 24) * ratio / 1000}];
  }
}
```

This occurs after each memoized style selection, so reused component caches
still receive the override. The original style (including height, alignment and
shift) is preserved first in the array; no shared style object is mutated.
Unknown/native/build-55 IDs retain the exact original style object. Image URLs,
animated/static selection, `contain` mode, decoder and playback remain unchanged.

The primary width evidence is provider metadata, notably 7TV's dimensions.
Unknown dimensions use a square; header dimensions learned later do not reflow
an already-frozen alias in this experiment. Ratios above 5 are width-capped and
remain contained inside the original-height box. Very narrow ratios are floored
at 0.125. This is not zero-width/overlay emote composition support.

## Host and donor verification

The production patch code is `TASRNWidthPatch.h`; the source hook, aliases and
existing redirect live in `TASEmotes.c`. Host tests cover:

- Exact-body header/footer/format refusal, unchanged caller buffer, original
  function/data preservation, new length/header and patch extent, re-patch refusal.
- Emitted instruction semantics for native/string/old IDs, bounds, square, wide,
  narrow and enlarged styles; original style identity preservation.
- Source getter ABI/ownership/idempotence, disabled and refused object identity,
  once-per-source refusal and source-owned cache.
- RN-only alias emission, native ranges/body preservation, redirects, frozen
  dimensions, safe collisions, and historical alias mapping.

The synthetic fixture isolates container logic and does not pretend to be a
runnable Twitch bundle. The independent donor check uses actual SHA-1 and parses
the real body. It confirms:

- Only function 19127 changes: 947 → 1,207 bytes; original code is retained.
- Both 130-byte style blocks use existing dead Value registers. Frame size,
  register-bank counts, constant pools, cache sizes and all other headers stay
  unchanged. No call layout or function index changes.
- All **34** original branch targets remain correct without displacement edits.
- Only **8** original-body bytes differ, solely within file length and that
  function's offset/size; the appended body and new SHA-1 footer validate.
- An independent Hermes-98 compiler successfully disassembles the entire
  rewritten container. This is not VM execution or an iOS Fabric render test.

Reproduction (analysis dependencies only: hermes-dec 0.1.7 and optional
hermes-compiler 250829098.0.19, HBC 98):

```sh
ZIG=/path/to/zig python3 tools/verify_rn_width.py /path/to/twitch-31.5.ipa \
  --hermesc /path/to/hermesc
ZIG=/path/to/zig EMOTE_DIAGNOSTIC=0 make verify test
```

## Device test and reports

1. Sign/install build 56. Enable third-party emotes, fully terminate/relaunch,
   and enable diagnostics. Capture A before chat: label `3.0.0-build.56`,
   source hook installed. Patch activation can wait until the first RN surface
   loads. After entering chat, expect `installed/yes` and patched bodies ≥1;
   if still inactive, capture that report and expect the square fallback.
2. Receive known 7TV **wide static, wide animated and square animated** emotes
   from other users, preferably beside normal text and native Twitch emotes.
   Capture a screenshot and report B. Wide emotes should retain normal height
   and gain width; square/native emotes should keep their shape and size. Text
   after an emote must start after the complete image, and wrap without overlap.
3. Scroll offscreen/back, switch channels and repeat. Confirm correct bitmap
   identity, continuing animation, and unaffected native/plain-text messages.
   Capture C. If available, also test enlarged emotes and a message wrapping at
   the right edge. Sending from this account is not an acceptance case.

New sanitized counters report source-hook installation, patch activation,
successful/refused source bodies and alias matches/collisions. Alias matches
count matcher activity, not unique images or proof of final delivery/layout.
Expected width collisions: zero. Legacy TextKit/image-layer sizing counters can
remain zero; they are not this active RN path. No chat text, identifiers, URLs,
source contents, raw pointers or image bytes are added to the log.

Validation: **66 host tests passed**, none skipped, including sanitizer-backed
production harnesses. Both framework/dylib artifact guards, Python compilation
and `git diff --check` passed with `EMOTE_DIAGNOSTIC=0`.

## Unsigned package provenance

`patch_ipa.py` and `verify_ipa.py` passed. Output:
`Twitch-31.5-Streamside-build56-incoming-width-unsigned.ipa`.
Size: 191,816,769 bytes; SHA-256:
`9517a2c421a289090726eb79de42fa4b8c34648bfcbcd45d7d69657eac2daa4f`.
Framework SHA-256:
`1bef448288924d5a45dad37a46db2eb1535cbd7f6505a2dc7b853ae124c2ae62`.

4,251 donor entries are byte-identical and none are removed. Only the main
executable's injection load header/padding and app display-name plist change;
the framework binary/plist are the only two added entries. The embedded bundle
and React framework remain byte-identical. Sign with the usual sideloading tool
before installing.
