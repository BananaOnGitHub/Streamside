# Twitch 31.5 native presentation trial — build 50

> Scope correction: this document describes the legacy chat path present in the
> Twitch 31.5 binary. Earlier device validation does not establish compatibility
> with the currently active React Native chat. See [the passive RN probe](RN_CHAT_BOUNDARY_PROBE.md).

## Result and scope

Implemented `TASEmotePresentation.c` on `compat/twitch-31.5`, following the
[native boundary investigation](TWITCH_31_5_PRESENTATION_BOUNDARY.md).
The subscriber-definition callback adds real provider `TKChatEmote` objects
for account-authored, current-channel text. The original `TWChatMessage`, its
token array and the `ChatMessageString` remain in place. Twitch performs text
matching, computes locations and constructs its own attachments.

The synthetic ID reaches the existing Streamside image-redirection and
proportional-geometry path. No alternate renderer or geometry implementation
was introduced. The normal build uses `EMOTE_DIAGNOSTIC=0`; no forensic branch
was merged. Main, diagnostic and archive branches are unchanged.

This is a test build, **not an on-device confirmation of the regression fix**.
There is no iOS device in the build environment. Static donor disassembly and
production-code host harnesses establish the path below; the tester must confirm
callback coverage, visible own-message rendering and animation playback.

## What the unlocked-emote object carries

The exact supplied donor is Twitch 31.5, build `262752111271985979`, main UUID
`6A2F9D5F-C563-3B41-9EDE-0CE9D0A0EFF5`. Addresses below are unslid evidence for
this donor, not production patch offsets. TwitchKit's preferred base is zero.

`TwitchKit.TKChatEmote` has these inspected native fields:

| Field | Donor offset / size | Presentation role |
| --- | --- | --- |
| `identifier` | 8 / 16 | Swift String bridged through the Objective-C getter; carries the existing synthetic decimal ID |
| `code` | 24 / 16 | Swift String; exact provider name used by Twitch's matcher |
| `modifiedEmotes` | 40 / 8 | Native array; the ordinary definition uses an empty array |
| `assetType` | 48 / 8 | Native integer; ordinary emote conversion passes 1 |

The definition has **no width, height or image URL field**. Dimensions and the
provider URL stay in Streamside's existing registry, joined by the synthetic ID.
The adapter calls `initWithIdentifier:code:modifiedEmotes:assetType:` with its
verified encoding `@48@0:8@16@24@32q40`. It verifies that the returned object's
identifier and code are unchanged, `isRegex` is false and `assetType` is 1.

The integer is grounded in five native constructor call sites, including the
ordinary `TWMessageEmoteToken` conversion at `0x100fc6784`. Each supplies
`w5 = 1` before invoking the native constructor. The other sites are
`0x10017d4f4`, `0x100d2cabc`, `0x103a78600` and `0x103d65220`.
This value is not used as a provider animation flag. No enum case name is
assumed from its integer representation.

## Identity and proportional geometry trace

| Boundary | Inspected behavior | Identity reaching the next stage |
| --- | --- | --- |
| Definition response | Renderer dispatches `currentChannelUnlockedSubscriberEmotesForMessageString:` on `ChatDataSource` / `ChatTranscriptView`, encoding `@24@0:8@16` | Real `TKChatEmote.identifier` and `.code` |
| Native text matcher | Worker `0x1042c03b8` splits on **literal U+0020 space**, looks up the exact code, reads definition getters | Unchanged synthetic identifier and provider code |
| Native presentation token | Creates `TWMessageEmoteToken` at `0x1042c06e0`; inserts it into `emoteLocationsMap` at `0x1042c0714` | `emoteId` is the definition identifier; Twitch computes the rendered location |
| Native attachment | Allocates plain `NSTextAttachment` at `0x1042c0900` and appends its attributed string at `0x1042c0954` | Location map links the attachment character to the presentation token |
| Image data | Worker `0x1042bb2b4` reads token `emoteId`, builds `/emoticons/v2/{id}/...` URLs and native `MessageStringImageData` | Synthetic ID remains in the static/default/animated Twitch URL paths |
| Image layer | `ImageAttachmentLayer.content` contains a CGRect followed by `MessageStringImageData`; static/animated URL getters survive | Existing `image_layer_id` parses that same synthetic ID |
| Streamside sizing and image redirect | Registry resolves `tas_emotes_aspect(id)` and provider URL from the ID | Same registry entry as incoming provider emotes |

The native attachment begins with square bounds. Therefore the retained
TextKit hook is essential: it resolves `MessageStringLayoutManager.messageString`
and its location map, obtains the synthetic ID, and reserves proportional
attachment width. Layer-frame handling separately applies the same registry
ratio to the image layer. Merely painting a wider image would leave incorrect
text wrapping and attachment spacing.

Both handlers are unchanged. The donor's named layout-manager field is a strong
object, and the image-layer content spans 40 bytes before
`networkImageRequester`: CGRect (32 bytes) plus image-data reference (8 bytes).
Existing code resolves field offsets at runtime and rejects unexpected spans;
these observed offsets are not hardcoded by the new adapter.

Native construction/copy/update call sites store `ChatMessageString.chatMessage`
before invoking its formatting worker. The new callback can read the original
message through that getter without replacing it. The original `messageTokens`
array receives no presentation-token write.

## Admission and ownership

- Call the original subscriber IMP first; preserve its native definitions.
  Read the saved original follower IMP only to exclude native-code conflicts;
  the follower method itself is not swizzled or enriched.
- Compare the original message's `senderId` with a live emote manager's current
  user. Resolve the receiver's own channel; there is no last-channel fallback.
  Read named fields only after class, alignment, next-field-span and instance
  bounds checks. Optional UInt32 values must have a present discriminator and
  a nonzero value. Unknown layouts pass through.
- Data-source scope uses its live `emoteManager` reference. Transcript scope
  uses a weak manager reference observed from the data source or three actual
  native account callback selectors. The inspected manager initializer
  registers the account update/logout selectors with NotificationCenter.
  Reread `currentUserID` for each render; do not retain an account-ID snapshot.
  No observed manager, or multiple distinct observed live managers, disables
  transcript enrichment. Device testing must confirm initialization coverage.
- Scan only exact ordinary `TWMessageTextToken` instances. Moderated/censored
  text subclasses cause the entire message to pass through because Twitch's
  emote match precedes its moderation fallback. Historical messages and
  shared-chat messages from other channels pass through.
- Existing native emote-token names and both native definition arrays take
  precedence. Preserve URLs, mentions, bits and GIF token branches. Match the
  native literal-space boundary and case exactly; punctuation, tabs and newlines
  are not normalized into names.
- Use only the loaded provider registry. No catalog fetch, sorting or network
  wait occurs in the presentation callback. Bounds: 128 tokens, 4,096 UTF-16
  units per text token, 512 space-separated pieces and 64 provider definitions.
- Construct definitions with normal +1 initializer ownership; append to a copy
  of the original array only when a provider matches, release owned values and
  return the array at +0. No message pointers are retained for a later rebuild.

The existing legacy local-delivery adapter remains unavailable on this donor
because its installation prerequisites are absent. This trial does not force
its old message constructor or modify the WebSocket/composer paths.

Normal sanitized status reports add aggregate hook/callback/admission/skip
counters. They retain no chat text, sender/channel IDs or provider URLs.

## Host validation and required device matrix

Three production-code harnesses cover the definition adapter, real provider
registry/image-request redirection, and existing TextKit/layer geometry.
They run with AddressSanitizer and UndefinedBehaviorSanitizer where applicable.
The geometry matrix at a native height of 28 points is:

| Fixture | Ratio | Attachment / layer size | Image-request coverage |
| --- | --- | --- | --- |
| Static square | 1:1 | 28 × 28 | Static, default and animated native URL modes |
| Static wide | 4:1 | 112 × 28 | All three modes |
| Animated square | 1:1 | 28 × 28 | All three modes; GIF provider mapping |
| Animated wide | 3:1 | 84 × 28 | All three modes; GIF provider mapping |

The adapter harness verifies synthetic ID/code round trips, original message
and token preservation, repeated formatting, duplicate/native-name conflicts,
account changes/nil account, missing/ambiguous transcript authority, bad layouts
and method encodings, moderation, historical/shared-channel messages and exact
text boundaries. The real registry harness verifies ID-to-ratio and ID-to-URL
lookup, preserving the original image request. The geometry harness checks both
reserved TextKit width and painted layer width, including repeated frame updates.
Native emotes and unknown image hosts retain their normal behavior.

These are host fixtures, not provider downloads played by Twitch on iOS.
The native Swift matcher and image builder are traced by disassembly, not
executed by the host harness. GIF URLs establish the routing path, not successful
animation decoding, timing or playback.

Device acceptance requires sending each of the four shapes from the account
and comparing it with an incoming instance of the same emote. Check visible
proportions, reserved spacing/wrapping, baseline, tapping and scrolling/reuse.
Both animated cases must advance while visible, including the wide animation.
Repeat ordinary typing and picker insertion, replies, channel/account changes,
native-name conflicts and moderation/shared-chat cases. Any square-only wide
render or incorrect text reservation is a regression even if the image loads.

## Build and package verification

`EMOTE_DIAGNOSTIC=0 ZIG=/path/to/zig-0.14.0/zig make verify test` passed:
all **60 tests**, none skipped, and framework/dylib Mach-O artifact checks.
The unchanged patcher successfully produced
`Twitch-31.5-Streamside-build50-test-unsigned.ipa`; `verify_ipa` passed its
archive CRC, duplicate-entry, required-load and framework-byte checks.

- Framework bundle version: `3.0.0.50`; report label: `3.0.0-build.50`.
- 4,251 donor entries are byte-identical. No donor entry was removed.
  Only the app executable's injection header/padding and app display-name plist
  changed. The framework binary and its plist are the only two added entries.
- The main executable has the same size, original load commands and executable
  code/data. Exactly one required framework load command was added in empty
  padding. App plist keys differ only in `CFBundleDisplayName`/`CFBundleName`.
- `Assets.car` is unchanged, SHA-256
  `903ef7e19e7b553d60b252695b75888b173b019522e0f5a9c9de9a8eb6e4af96`.
- Normal framework contains the presentation counters and no `Inspect Emote`,
  rolling playback, decode provenance, decode-handoff or request-decision
  markers.
- IPA size: 191,813,175 bytes; SHA-256
  `dec43054781ed3243e3467c8556af6aa3bd2390ee90927953498fa13ff0ab59e`.
- Packaged framework SHA-256:
  `0a172245a8a9363c1eeceac03c8b802829710827bdbd918c81c5915641ae68b5`.

The output is unsigned. Sign it with the tester's usual sideloading tool,
including the embedded framework and extensions, before installation.
