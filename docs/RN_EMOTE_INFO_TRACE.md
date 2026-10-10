# Twitch 31.5 RN emote info investigation — build 65

> Archived at `archive/rn-chat-boundary`. Later compat build-66 evidence confirmed provider tap/host/sheet execution without query-backed native card content; compat supplied the provider card at that boundary. This build-65 probe and its historical trial remain preserved. See [branch closure](BRANCH_ARCHIVE.md).

## Result

Static tracing identifies an RN info path. Runtime activation and the provider
tap behavior still need device evidence, so this build instruments that path
instead of shipping an unverified replacement. The user confirms build 64
composer images, proportions and first-download GIF playback work.

`diagnostic/rn-chat-boundary` and compat had diverged after build 51. A merge
brings the diagnostic branch forward to compat build 64 while retaining its
build 51–54 probes, tools, tests and docs. Both heads remain in history; no
force update or diagnostic reset. Production probes remain compile-time off
unless `RN_CHAT_DIAGNOSTIC=1`. This trial uses that flag with
`EMOTE_DIAGNOSTIC=0` to avoid the older per-word/image forensic recorder.

## Exact donor trace

Verified donor IPA SHA-256:
`718762b71095c11754b1f58ad01fb580852414e6d7f468fbb2236b7c2419e641`.
Hermes-98 bundle SHA-256:
`422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b`.

| Boundary | Function | Evidence |
| --- | ---: | --- |
| EmotePart render | 19127 | Receives `emoteId` and optional `onPress`; wraps the image in a tappable RN Text only when the callback is present. This is the already working proportional-width target. |
| Ordinary chat part render | 35357 | For emote parts, creates callback 43823 when its parent press callback exists. |
| Emote tap | 43823 | Reads the part's `emoteId` and `text`, calls the parent handler with both. The diagnostic reads only the ID; original token handling stays intact. |
| Chat card host | 19174 | Metro module 3797 / factory 3801 exports `ChatCardHost`. For `openCard.kind === "emote"`, creates function 19172 with ID, token, channel, message, author and close props. Suppressed/empty/viewer states take other paths. |
| Emote sheet | 19172 | Calls `useQuery(EMOTE_CARD_QUERY, {variables:{emoteID},fetchPolicy:"cache-and-network"})`. Reads loading/error/data and renders RN `BottomSheet`; calls the EmoteCard content only with successful emote data. |
| Card content | 19704 | Metro module 4052 / factory 4056 exports `EmoteCard`. Receives emote, image URL and Twitch follow/subscription/report/navigation actions. Uses theme/intl and Twitch card components. |

Function 19692 is the general RN BottomSheet component; its implementation
uses `Modal`. It is **not a separate emote popup route**. Initial string-level
searches are insufficient to infer an alternate active emote presentation.
The current tap-to-host state dispatcher and feature/runtime gates are not
yet independently confirmed on-device.

Provider synthetic IDs cannot be assumed to resolve through Twitch's EmoteCard
query. A replacement needs a provider metadata source and separate RN content
while retaining the native Twitch popup behavior for Twitch IDs. Reusing the
unmodified card would expose Twitch ownership/entitlement actions that do not
describe 7TV/BTTV/FFZ emotes. Branching before hooks inside the existing sheet
also risks changing React hook order; a separate component boundary is needed.

## What the diagnostic measures

Five exact-body-gated prefixes call the existing separate NativeModules module
with `trace(seam, identifier, handlerPresent)`. Native code immediately
classifies and discards the identifier. No props objects, callbacks, token
text, channel IDs, message IDs, query variables or URLs cross this diagnostic
bridge. No identifier values, fingerprints or per-message events are retained.

The report section `RN emote info trace` records:

- Whether all five prefixes were admitted and the export was discovered.
- Counts at each render/tap/host/sheet/content boundary.
- Ordinary-ID, resolved-provider, unresolved-provider-candidate and missing-ID
  classifications for each boundary. The ordinary category is an inference
  from the existing synthetic-ID namespace, not a Twitch API validation.
- EmotePart calls with/without a tap handler.
- Refused native arguments and refused patch admission.

These are render counts, not unique popup openings. Host counts include its
empty/viewer renders and therefore often have no emote ID. Existing passive
boundary probes remain available in the same report. Clearing the disk log
does not reset launch counters; full app restart does.

## Fail-open behavior and validation

The patch runs only after the existing exact donor width/local/composer gates.
All five headers are admitted together. Function bodies are copied verbatim
after the diagnostic prefix, preserving every original relative branch and
the working width additions. Constant pools, environments, React hooks and
existing exception/debug tables remain unchanged. A prefix exception resumes
the original body; it never overrides return values, sends, selection or UI.

The tap's frame grows from 14 to 24 so Hermes Call4 staging cannot overwrite
its diagnostic callee/arguments. Its original Call3 uses explicit operands.
All other frames are unchanged. The original on-disk bundle is unchanged.

Validation commands:

```sh
ZIG=/path/to/zig RN_CHAT_DIAGNOSTIC=1 EMOTE_DIAGNOSTIC=0 make verify test
PYTHONPATH=/path/to/analysis-deps ZIG=/path/to/zig python3 tools/verify_rn_width.py \
  /path/to/tv.twitch-31.5.ipa --local --composer --hermesc /path/to/hermesc
PYTHONPATH=/path/to/analysis-deps ZIG=/path/to/zig python3 tools/verify_rn_info.py \
  /path/to/tv.twitch-31.5.ipa --hermesc /path/to/hermesc
```

The exact-donor validator checks all original bytes/branches, five isolated
Catch tables, frame sizes, constant pool/header/debug preservation, footer,
repeat/malformed admission refusals, and independent Hermes-98 disassembly.
Prefix tests cover all seams, missing modules/IDs, sequential call staging and
exceptions at every native lookup/call. Host checks establish structure and
fallback, not actual Fabric dispatch or visible popup behavior.

Build 65 validation completed: framework/dylib artifact checks; 87 tests
(one skipped); production width/local/composer donor validation; all five
info seams independently disassembled; unsigned IPA verification. The packaged
Hermes bundle and React framework remain byte-identical to the donor. Framework
SHA-256 is `5161f2fe98d47f208888cf9471335ea41f9a3d46a7a58fd53481528fd7ec97f0`.

## Device trial

1. Sign/install build 65 and fully restart Twitch; enable diagnostics and
   third-party emotes before launch.
2. In live chat, tap one visible Twitch emote and dismiss its info popup.
3. Tap one visible 7TV emote in a received or own sent chat message. Record
   whether it opens a sheet, shows a loading/error state, or does nothing.
4. Optionally hold a provider preview in the composer to compare that separate
   native attachment gesture; the new prefixes target the chat popup path.
5. Export one same-launch report. Include the two observed tap outcomes.

Expected decision: tap + host + sheet provider counts with no card content
places the needed replacement at the provider data/content branch. A tap with
no provider host/sheet counts means the dispatcher needs tracing next. Provider
render counts with no tap handler means the chat callback wiring must be fixed
before popup content work. Zero counters with an active patch require verifying
the native module export/call path rather than assuming the UI seam executed.

The picker/catalog implementation remains a later milestone.
