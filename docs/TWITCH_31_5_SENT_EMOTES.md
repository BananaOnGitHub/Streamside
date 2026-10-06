# Twitch 31.5: constraint cleanup and sent-emote investigation

This is the historical build-49 investigation. The subsequent
[build-50 presentation trial](TWITCH_31_5_PRESENTATION_TRIAL.md) implements
native definition enrichment and checks synthetic identity and variable widths.
Device validation of that trial is pending.

## Status

The tester reports that the build-48 IPA is mostly fully functional on Twitch
31.5. Third-party emotes preview correctly in the composer but do not render in
the tester's own sent chat messages. This investigation uses the same supplied
decrypted donor identified in [the build-48 report](TWITCH_31_5_COMPATIBILITY.md).

Build-49 source changes are isolated on `compat/twitch-31.5`. Main, diagnostic
branches and archives are unchanged. The sent-message adapter is not repaired
by this change; the findings below identify why it no longer installs.

## Removed constraints

- Removed the marketing-version allowlist from `SSComposer.c`'s native catalog
  admission. Class, dynamic-symbol, ivar-offset, instance-bounds and Swift
  value-witness-size checks remain mandatory. Unsupported layouts still fail
  closed rather than being interpreted as native catalog values.
- Replaced the fixed input-delegate offset with runtime field resolution.
  Delegate storage must be aligned, occupy two pointer words before
  `inputMode`, and fit the instance. Twitch 31.5's donor metadata puts these
  fields at 560 and 576. Its `textViewDidChange:` worker uses
  `swift_unknownObjectWeakLoadStrong` on that storage and later releases the
  retained object with `swift_unknownObjectRelease`.
- Removed active old-version references from source and current integration
  documentation. Historical release/history/build reports retain accurate
  provenance; they are not compatibility restrictions.
- Removed the old donor UUID/return-address classifier from the temporary
  image probe. Without a current validated map, callers remain `unknown`.
  This probe remains compiled out of normal builds (`EMOTE_DIAGNOSTIC=0`);
  no commits from the forensic branches were incorporated.

## Confirmed break in the local-delivery adapter

The old path in `TASEmoteUI.c` hooks local chat delivery, matches only the
account's own messages, splits matching text tokens into provider emote tokens,
and reconstructs a native message while retaining its metadata. Inspection of
the supplied donor's Objective-C class/method metadata and selector strings
found these incompatibilities:

| Adapter dependency | Twitch 31.5 donor evidence | Consequence |
| --- | --- | --- |
| `TKIdentity` and its identity initializer | Class absent from inspected main/TwitchKit class metadata | Installation prerequisite fails |
| `TWMessageTextToken.initWithText:autoModFlags:` | Absent; `initWithText:` survives with encoding `@24@0:8@16` | Another installation prerequisite fails; old reconstruction call is invalid |
| `TwitchChatController.chatManager:receivedMessages:for:on:` | Absent from inspected metadata/selectors | Old local-delivery hook target is gone |
| Full `TWChatMessage` tokens/sender/badges/date/IDs/color/flags/kind/modes/type/tags initializer | Absent; `initWithMessageTokens:` survives | No equivalent metadata-preserving reconstruction bridge established |
| Text token `autoModFlags` and message `flags` / `userModes` getters | Swift ivars remain, but these Objective-C getters are absent | Old getter calls are invalid; reading raw Swift storage is not a replacement |
| `TWMessageEmoteToken.initWithEmoteId:emoteText:` | Present, encoding `@32@0:8@16@24` | Native emote token construction itself remains exposed |
| `TWChatMessage.messageTokens` | Present, encoding `@16@0:8` | A token-reading bridge remains exposed |

At least three independent installation requirements fail. This explains why
the account's local chat echo does not receive Streamside's synthetic emote
tokens. This is not evidence of a provider matcher or image-download failure,
and removing the catalog's version allowlist does not fix this separate path.
Renaming an identity class alone would leave missing methods and unsafe calls.

Composer previews use a separate provider-image path. On send, Streamside
restores the original emote names as text by design. Incoming WebSocket
rewriting is also separate. Thus composer previews and incoming emotes can work
while the local sent-message enrichment is unavailable.

## Replacement boundary to investigate

The subsequent [native presentation-boundary trace](TWITCH_31_5_PRESENTATION_BOUNDARY.md)
identifies a stronger seam: the renderer's per-message emote-definition
callback. It establishes real Objective-C dispatch and native
text-to-attachment construction. The initial candidates below are retained
as investigation history; the trace explains why they are less suitable.

The donor retains presentation-side Objective-C surfaces:

| Class | Candidate surface | Encoding |
| --- | --- | --- |
| `ChatMessageString` | `rebuildTextStorage` | `v16@0:8` |
| `ChatMessageString` | `chatMessage` / `setChatMessage:` | `@16@0:8` / `v24@0:8@16` |
| `MessageString` | `message` / `setMessage:` | `@16@0:8` / `v24@0:8@16` |
| `MessageString` | `setEmoteLocationsMap:` | `v24@0:8@16` |
| `ChatMessageTableViewCell` | `apply:` | `v24@0:8@16` |

These are candidates, not a proven adapter. Direct Swift calls can bypass
Objective-C wrappers; selector presence does not establish hook coverage.
`WrappedChatMessage` does not expose a usable Objective-C message getter in
the inspected method table.

A replacement should preserve the original message and its moderation,
sender, native-token and URL metadata, establish the correct channel scope,
and enrich presentation without changing outgoing IRC/GraphQL text. It needs
call-path validation and device tests before being described as a fix. Do not
force the removed initializer, guess Swift model layouts, or drop moderation
flags just to use the shorter text-token constructor.

## Verification

`EMOTE_DIAGNOSTIC=0 make verify test` succeeded using Zig 0.14.0:

- All 58 tests passed; none skipped.
- Framework/dylib Mach-O layout and artifact contracts passed.
- New native-catalog harness exercises missing capabilities, incompatible
  layouts and relocated/missing/misaligned/out-of-bounds delegate storage.
- Probe tests verify that unclassified callers remain unknown.

These are build/static/harness checks, not iPhone runtime validation. Build-49
native catalog admission still needs device validation. No new IPA was
packaged for this investigation, and no sent-message regression fix was
implemented.
