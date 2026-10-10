# Twitch 31.5 RN emote representation

> Archived representation analysis on `archive/rn-chat-boundary`. Its code-to-ID map, Unicode range and ID-to-image URL findings informed compat's later incoming rendering and local-echo adapters. Static feasibility statements below retain their original evidence limits. See [branch closure](BRANCH_ARCHIVE.md).

## Scope and evidence level

Investigate the 951-entry composer catalog and incoming synthetic metadata
before returning to local echo. This is static, read-only donor analysis plus
the build-52 passive device observations. No JS injection, catalog mutation,
message rewrite, image redirect or geometry change is added here.

Donor SHA256: `718762b71095c11754b1f58ad01fb580852414e6d7f468fbb2236b7c2419e641`.
Its embedded Hermes-98 bundle has 27,786,480 bytes and FNV64
`3c748f1f3e33577c`, matching the RCTSource body observed in builds 51 and 52.
Function numbers and offsets below identify this bundle only; a matching source
fingerprint is not proof that each static function executed.

## Representation at each boundary

| Boundary | Representation in the traced bundle | Evidence |
|---|---|---|
| ChatEmoteSets response schema | Sets with emotes containing `id`, `setID`, `token`, `type`, `assetType`, and modifier codes; owner metadata is separate | Module 3676, `CHAT_EMOTE_SETS_QUERY` |
| Flattened catalog item | `{id, token, setID, type, ownerID, setName, avatarURL, ownerLogin, modifierCodes}` | `flattenEmoteSets`, function 18859 |
| Chat-client/native-composer map | Token or supported alias → emote ID; values are IDs, not image URLs or full definitions | `buildEmoteTokenMap`, 18161; shared handoff in 21334 and 37048 |
| Native token-image map | Separate cheermote token-image data; empty in the device test | ChatComposerBar 22083; build-52 setter observations |
| Parsed incoming `emotes` tag | Array of `{id, start, end}`; ID is a string, positions are numbers, end is inclusive | `parseEmotes`, 18143; `parseChatLine`, 18147 |
| Transcript segment | `{kind: "emote", key, text, emoteId}`; `emoteId` is the range ID | `segmentMessageBody`, 18057 |
| RN image component | EmotePart receives `emoteId`, constructs a Twitch CDN URL, supplies it to CoreImage | Part mapper 35357; EmotePart 19127 |
| Layout | Fixed square wrapper and image: 24×24 inline, 56×56 gigantified | Module 3780 and EmotePart 19127 |

The common identity is the emote ID string. Catalog presentation fields,
provider/aspect metadata and image dimensions are not carried in the normal
incoming emote segment.

## The catalog and its two consumers converge

`flattenEmoteSets` (18859, bundle offset `0x01480937`) walks
`currentUser.emoteSets`, ignores entries without an ID/token, and deduplicates
by token. It keeps the ID and token unchanged and adds set/owner display fields.
The query and this flattening step do not supply emote image dimensions.

The main chat component (21334, `0x0156635e`) reads
`useChatData().emoteSuggestions` at bytecode `0xe16`. At `0xef1–0xf63` it builds
the token map from suggestions plus eligible modified-emote entries.
`buildModifiedEmotes` (18858/35139) derives modifier IDs and tokens by appending
`_` plus the modifier code.

`buildEmoteTokenMap` (18161, `0x014575a1`) has the following semantics:

```js
// Read-only reconstruction, not code installed in Twitch.
const map = {};
for (const emote of emotes) {
  if (!emote.id || !emote.token) continue;
  for (const alias of emoteTokenAliases(emote.token)) {
    if (!Object.hasOwn(map, alias)) map[alias] = emote.id;
  }
}
```

The alias helper (18160) returns a predefined alias list when one exists,
otherwise `[token]`. First ownership of a key wins. Consequently, a count of
951 keys is not necessarily 951 distinct emote IDs, source records or picker
rows: aliases, token deduplication, collisions and modifiers affect the count.
The passive reports do not retain enough data to reconstruct the exact 951
entries, nor should this analysis invent them.

Crucially, there are two handoff names but not two independently built maps in
this component. The map result stays in register 136:

- `0xf79` stores it in environment slot 48. Effect 37048 (`0x0181fa0e`)
  calls the chat store's `getState().setEmoteTokenMap` with that value.
- `0x942f` passes that same value as `ChatComposerBar.emoteMap`.
- ChatComposerBar 22083 passes it to AutocompleteTextInput 21415, then
  EmoteTextInput 19088, which hands it to the native emote input component.

This static chain explains the observed string-valued dictionary at
TwitchEmoteInputView.setEmoteMap. It does not establish runtime pointer identity
across JS and Foundation bridging, enumerate the live keys, or prove that
mutating the native setter would update the JS chat store or picker sections.
Picker sections/suggestions are upstream catalog data, not this map alone.

AutocompleteTextInput's URL templates (module 4623) are built with
`makeEmoteURL("__ID__", {scale, animated})`, replacing the placeholder with
`{id}`. Animated and static templates are selected separately. This corroborates
the code → ID → templated URL contract; the map is not a code → URL dictionary.

## Incoming metadata to RN emote presentation

`parseChatLine` (18147, `0x01456b76`) reads the incoming PRIVMSG's `emotes` tag
and assigns `parseEmotes`' output to the returned message's `emotes` field.
`parseEmotes` (18143, `0x01456598`) splits slash-separated ID groups and
comma-separated positions. It slices the ID before `:` without numeric
conversion, converts only positions to numbers, and rejects NaN positions.

The body component 19139 (`0x01492b6e`, call at `0x196`) passes body text and
emote ranges to `segmentMessageBody` (18057, `0x01452c8b`). That function:

- Uses `Array.from(body)` for Unicode code-point indexing.
- Filters ranges for `start >= 0`, `end >= start`, and `start < body length`
  (34170), then sorts by start (34171).
- Skips ranges beginning before the already-consumed position and clamps an
  oversized end to the final code point.
- Creates an emote part with the range ID unchanged in `emoteId` and the
  covered text in `text`. No catalog membership lookup occurs in this step.

Part mapper 35357 (`0x017f9dfe`, bytecode `0x219–0x24a`) passes the part's
`emoteId` directly into EmotePart. EmotePart (19127, `0x01491a79`) constructs:

```text
https://static-cdn.jtvnw.net/emoticons/v2/<emoteId>/<default-or-static>/dark/<scale>.0
```

It interpolates the ID without numeric conversion or catalog lookup, then
passes the URL to CoreImage with `resizeMode: "contain"`. The inspected normal
part path therefore has no catalog-ID allowlist that would itself reject a
synthetic decimal ID. This is static feasibility, not a runtime synthetic-ID
rendering result or proof that every message variant uses this path.

## Implications for Streamside synthetic metadata

The existing legacy `rewrite_line` in `src/TASEmotes.c` already appends
`<synthetic-id>:<start>-<inclusive-end>` to IRC `emotes` metadata, using Unicode
code-point positions and preserving native overlaps and message body text.
Its decimal synthetic identity matches the inspected RN parser/part/URL
contract. The active RN receive route bypasses that rewrite today.

`tas_emotes_rewrite_request_copy` recognizes the Twitch `/emoticons/v2/`
synthetic-ID URL and resolves it to the provider asset. Its URL recognition
accepts the RN default/static suffixes; whether the active RN HTTP path reaches
the existing interception and decodes the provider asset is still unvalidated.
Build 52 supplied no synthetic IDs, so its zero provider requests cannot answer
that question.

Incoming tagged emotes do not require a matching catalog entry in the inspected
segment/render path. Catalog integration and incoming metadata can therefore be
validated separately while sharing one synthetic-ID registry. That is a design
inference, not an implemented compatibility feature.

Image loading alone is insufficient. The fixed RN wrapper/image squares contain
no provider aspect field. Redirecting a wide asset would still leave a square
layout box. A compatibility implementation must carry provider identity/aspect
to RN layout and validate transcript wrapping, not merely stretch a native
image view after Fabric layout. Legacy TextKit/layer sizing is not this path.

## Next validation gates; local echo deferred

1. Finish passive catalog attribution: aggregate key types, distinct ID counts
   and repeated-value counts. Build 53 observes these per weak native input
   instance and attempts theatre surface attribution. Repeated values can be
   aliases, but do not prove alias generation or token collisions. Exact overlap
   with incoming native-emote IDs is not measured: build 53 retains no IDs or
   ID fingerprints across callbacks. Confirm active-room provider scope separately.
2. Confirm the native composer consumer's ID-template contract and the incoming
   part/image identity boundary at runtime. No catalog injection or synthetic
   receive frames belong on `diagnostic/rn-chat-boundary`.
3. After explicit functional-test authorization, use `compat/twitch-31.5` for
   an incoming-only synthetic-ID test. First prove receive rewrite → emote URL
   → provider request/decode → displayed emote, then square/wide/animated and
   animated-wide layout. Keep native metadata and unrelated images unchanged.
4. Integrate provider catalog items upstream if picker/catalog behavior is
   required; changing only a native map setter cannot establish JS catalog
   compatibility. Preserve native-token ownership on collisions.

Do not add send/local-echo probes or change echo behavior in this phase. The
eventual echo investigation can use the now-identified token map, ID-bearing
range and RN emote-part shapes as concrete search targets.

Build 53's runtime gate is structural only: native catalog key/value types,
distinct bounded string values, template categories, URL construction during
native input updates, and real incoming tag ID/range shapes. It supplies no
synthetic IDs and does not directly instrument JS tokenization or the RN part
mapper. Positive observations corroborate the contract above, not end-to-end
synthetic emote compatibility. See `RN_CHAT_BOUNDARY_PROBE.md` for the staged test.
