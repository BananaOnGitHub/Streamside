# Build 53 device findings and next diagnostic

Reports A–C are cumulative from one launch on Twitch 31.5
(`262752111271985979`). The consumed embedded Hermes-98 source remains
27,786,480 bytes, FNV64 `3c748f1f3e33577c`. The fingerprint identifies the
observed source; it does not prove every statically traced function executed.

## Device evidence

| Observation | A: baseline | B: incoming | C: picker, unsent |
|---|---:|---:|---:|
| IRC deliveries / PRIVMSG / emote-tagged PRIVMSG | 0/0/0 | 474/470/21 | 858/852/44 |
| Nested IRC websocketMessage emissions | 0 | 474 | 858 |
| Nonempty composer map / cumulative entries | 0/0 | 1/951 | 1/951 |
| Latest map entries / distinct strings / repeated values | unobserved | 951/921/30 | 951/921/30 |
| Map values decimal / opaque / URL / empty / oversize | unobserved | 385/566/0/0/0 | 385/566/0/0/0 |
| Map/template getter calls | 0/0 | 1/1 | 1/1 |
| Empty/nonempty input value assignments | 0/0 | 1/0 | 1/1 |
| Composer square/wide attachment bounds calls | 0/0 | 0/0 | 3/0 |
| Emote URL factory/init observations | 0/0 | 200/350 | 200/497 |
| Input-nested/native-input-caller URL observations | 0/0 | 0/0 | 0/0 |
| Incoming tag ID groups decimal/opaque | 0/0 | 3/19 | 4/42 |
| Ordered/reversed/invalid tag ranges | 0/0/0 | 49/0/0 | 88/0/0 |
| Twitch emote URL loader/HTTP requests | 0/0 | 263/262 | 371/370 |
| HTTP SendChatMessage requests | 0 | 0 | 0 |

B and C place input slot 1 in `TwitchRNTheatre`. All 951 keys and values in
the latest map snapshot are strings. There are two snapshots, not 951 unique
emotes: 30 entries repeat an existing value. This is consistent with aliases,
but neither alias provenance nor modifier semantics is established by counts.
Opaque values are normal in authentic catalog and incoming metadata; they are
not proof of third-party IDs or runtime support for Streamside synthetic IDs.
The template setter is categorized as the native default CDN format. The empty
token-image dictionary is separate from the emote map.

Both getter first callers are `React+0xdde2c`; their traffic is consistent with
React property plumbing rather than demonstrated native token lookup. Neither
getter gains a call between B and C. The latest recorded map snapshot is
unchanged; that is not proof the live dictionary cannot change internally.

C adds one nonempty native value assignment and three square attachment bounds
calls. Repeated sizing calls do not count distinct emotes. These observations
do not independently confirm that the composer image was visibly displayed.
No send is requested, and local echo remains deliberately deferred.

The URL observation gap persists: all observed emote URL constructors remain
outside the synchronous input/caller categories. Alternate Swift construction,
asynchrony and caching are possible explanations, not determined causes. Zero
attributed constructors does not establish failed loading. The hook's first
caller row concerns its first global call, not its first emote-specific call.

Incoming ID group/range totals are repeated observations, not unique IDs or
validated body positions. No reversed/invalid range or budget refusal occurred.
Header-only shape inspection still does not observe JS parsing, part mapping,
catalog membership, or synthetic metadata consumption. Legacy provider matching,
rewriting, image and composer paths remain inactive despite successful provider
registry fetches. One generic HTTP completion error appears in B and persists
in C; it is not attributed to an emote request.

The three clean unmapped HLS variants occur at initial overlapping master
refreshes, with retired-route matches aged 0–2 seconds. Their total does not
increase in B/C. This is separate from RN emote diagnostics. No ad-marked
manifest or HLS failure is recorded; ad suppression remains untested.

## Knoks's complementary render-boundary discovery

The supplied `CHAT_REVERSE.md` reports visible chat paragraphs in
`RCTParagraphComponentView` / `RCTParagraphTextView`, below fixed accessibility
identifiers `chat-message-line`, `chat-message-pressable`, `chat-message-row`,
`chat-message-list`, `chat-message-region`, and `chat-area`. A paragraph
description showed rich-text fragments and NSTextAttachments. Attachment
semantics were not resolved; they must not all be classified as emotes.
Getter inspection sometimes returned nil despite visible text. Parent scope is
therefore useful, while a nil attributed-text getter is only an observation gap.

These are collaborator observations, not independently reproduced runtime
results from the exact binary tested here. KMP class/method presence and
`managerImpls=0` / `observeHooks=0` do not identify an event entry point or its
transport. Missing WebSocket rows in those separate captures do not supersede
our positive IRC → RCTWebSocketModule → websocketMessage observations. The
render boundary is a complementary downstream candidate, not an established
replacement transport or complete message model. No private capture contents
are copied into this document.

## Required next diagnostic

Build 54 should observe the native attachment/image boundary and scoped RN
paragraph rendering without changing behavior. Inspect donor-defined methods
and exact ABI before hooking. Foundation inherited attachment image assignment
may be instrumented only with runtime guards and a native-attachment filter.
Use fixed scope categories and numeric image/attachment counts; never persist
chat text, tokens, IDs, URLs, ranges, payloads or arbitrary attribute dictionaries.
Avoid opaque C++ state decoding and guessed Swift storage offsets.

Repeat same-launch A baseline, B incoming, C one native picker emote left
unsent. Record whether its composer image appears. Optional D: clear the draft,
type one known native code, leave it unsent, and report whether an attachment
appears. No send/local-echo test or synthetic injection is needed. Installed
but unused hooks and unavailable getters must be reported as limitations.

## Publication

The build 52 findings and tested build 53 tree were successfully published to
`diagnostic/rn-chat-boundary`, head
`423858b9d042215b954326359ec081114eb77adb`. Earlier documentation's pending
publication note describes the initial approval failure, not the current state.
