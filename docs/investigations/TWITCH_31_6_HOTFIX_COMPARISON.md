# Twitch 31.6.1 and 31.6.2 donor comparison

Read-only investigation on `dev/3.1.0`, source `e7df790` (Streamside 3.1.0
build 17). Original donor archives are unchanged. No production code,
admission constants, version metadata or workflow changed; no new IPA was
generated. The investigation adds only this record, decoded inventory and an
optional owned host fixture/utility.

## Finding

**These supplied packages do not contain a new RN fix for the observed missing
redemptions.** The 31.6.1 Hermes body is byte-for-byte the previously recorded
31.5 body. The 31.6.2 body is byte-for-byte the original 31.6 body. Thus the
packaged RN sequence is **31.6 implementation → 31.5 implementation → 31.6
implementation**, despite the increasing application version/build labels.

The actual reward renderer was executed in pinned Hermes for all three donors.
An empty/whitespace redemption with no matching reward definition still returns
`null`, without throwing. A definition arriving later restores the notice.
Neither hotfix eliminates that reproduced condition.

31.6.1 has meaningful differences from 31.6 in surrounding RN features and
native executable sections. 31.6.2 restores the baseline RN implementation and
all 64 baseline framework executable sections. Its main executable has one
changed instruction, in Crashlytics, which resolves the same `objc_msgSend`
import through a different slot. This is not evidence of a chat fix.

These conclusions identify the **supplied artifacts**. They do not establish
why Twitch selected those contents, whether an external bundle updater later
replaces them, or the contents of every App Store distribution/experiment.

## Exact donor identities

All three use `tv.twitch`, executable `Twitch`, arm64 subtype 0, minimum iOS
16.4, SDK `iphoneos26.5`, Xcode build `17F42`. Inspected encryption IDs are
zero. The main executable's SHA-1 and SHA-256 CodeDirectory Info.plist slots
match the supplied plist bytes in each archive. This checks internal label
consistency, not Apple CMS authenticity or valid signing after decryption.

| Property | 31.6 | 31.6.1 | 31.6.2 |
| --- | --- | --- | --- |
| Bundle build | 262821841498166537 | 262862021310949730 | 262872150334984303 |
| IPA bytes | 197,132,043 | 195,178,314 | 197,132,394 |
| Main executable bytes | 108,159,824 | 108,331,392 | 108,159,824 |
| Main LC_UUID | `8f711ed6c2343300b541f2bd0100f1b7` | `51026d7d9cf23581ab88e82b579293c3` | `34613ae5d1e03658876de5e4d1cec6a6` |
| Frameworks | 64 | 61 | 64 |
| Main + framework/dylib Mach-O images | 66 | 63 | 66 |
| Hermes bytecode version | 98 | 98 | 98 |
| Original HBC bytes | 28,682,408 | 27,786,480 | 28,682,408 |
| HBC functions | 48,985 | 47,311 | 48,985 |
| HBC strings | 213,596 | 207,433 | 213,596 |
| Literal-value buffer bytes | 1,022,382 | 1,005,877 | 1,022,382 |
| Object-key buffer bytes | 284,664 | 277,435 | 284,664 |
| Object shapes | 13,620 | 12,890 | 13,620 |

IPA SHA-256:

- 31.6: `36d85ac4a7f0979ca392415af697a43fe7eb019f7fbfdf84dce18b7a25249cea`.
- 31.6.1: `1ab5c92ba56c72684fc12e9b53c9e4391215fd8beeb7b0bd29807711b7f83364`.
- 31.6.2: `8cf72803d0e0b1aeb7c062af2d0cbac1e20f78e9f3c73fc590ac5ae9d1d29186`.

Original HBC SHA-256:

- 31.6 and 31.6.2: `20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458`.
- 31.6.1: `422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b`.

The latter is the 31.5 identity recorded in the
[earlier donor inspection](TWITCH_31_6_COMPATIBILITY.md#inputs-and-identity),
not merely a similar length or function count. All original SHA-1 footers
validate. `hermesvm.framework` advertises 1.0.0/1.0.0 in all three; its UUID
`be274a2347cc3f5a9e988474553df5a8` and 1,849,828-byte `__text` are identical
(SHA-256 `9f5bc675604dfc430ef729bf1b875e5bdf6a9f327576b63987eca424d8cce02a`).
That metadata does not identify the donor engine's exact source commit. The
separately pinned host runtime is identified under validation below.

The [decoded inventory](TWITCH_31_6_HOTFIX_INVENTORY.json) contains every
framework name, bundle version/identifier, binary length, whole-binary hash,
UUID, encryption flag and executable-text hash, including the full main
executable hashes. It contains no donor instruction bodies or assets.

## Pairwise native comparison

Whole binary hashes change broadly and are insufficient evidence of changed
logic. Section comparisons exclude signing and outer ZIP metadata.

| Comparison | Common images | Whole-binary hashes changed | `__text` changed | Inventory change |
| --- | --- | --- | --- | --- |
| 31.6 → 31.6.1 | 63 | 62 | 9 | Three frameworks absent |
| 31.6.1 → 31.6.2 | 63 | 62 | 9 | Same three frameworks restored |
| 31.6 → 31.6.2 | 66 | 65 | 1 | Same framework inventory |

The absent/restored frameworks are
`Atomics_301F3DE065572157_PackageProduct`,
`DequeModule_307A0402D40AB265_PackageProduct`, and
`InternalCollectionsUtilities`.

The nine changed sections for comparisons involving 31.6.1 belong to `Twitch`,
`KMPMobileChat`, `OrderedCollections_1222128174265B56_PackageProduct`,
`TwitchCore`, `TwitchGraphQLAPI`, `TwitchKit`, `TwitchUtilities`,
`twitch_rn_debug_props`, and `twitch_rn_player`. Section differences establish
different executable bytes, but can include relocation/recompilation; they do
not by themselves establish a behavioral change in each framework.

Between 31.6 and 31.6.2, every framework's `__text` matches. Exactly one byte
in one four-byte main instruction differs, at `0x104fbe8f8`, in
`FIRCLSProcessRecordRuntimeInfo`: `ldr x8, [x8, #0x318]` becomes
`ldr x8, [x8, #0x320]`. Both slots bind `_objc_msgSend`; the subsequent runtime
address check has the same target. No changed chat/player instruction was
found in that main text comparison. Matching text does not assert identical
mutable data, remote flags, cached state or runtime scheduling.

Follow-up: the [splash activation investigation](TWITCH_31_6_2_SPLASH_ACTIVATION.md)
traces a native Eppo-controlled startup animation and confirms different bundled
production snapshots in 31.6 and 31.6.2, including 17 added/changed flag records.
The splash and RN eligibility rules themselves match. Executable equivalence
does not establish configuration equivalence or actual device assignments.

## Paused RN investigation is preserved

The starting evidence was read from
[`RN_CHAT_ROW_GAPS.md` at e26a4e2](https://github.com/BananaOnGitHub/Streamside/blob/e26a4e2f166872a970f35d81e8bc0c41236f326d/docs/investigations/RN_CHAT_ROW_GAPS.md)
on `fix/rn-chat-gaps`; its SHA-256 is
`d8626cac5e735716eecdcde02f0458bb3e2959538afc218885bd27496d0a8a2e`.
The branch, rolling observer, generated payload, compile-time gates and native
collector were not edited or reset.

Its distinctions remain essential: successful send/emission is not proof of
local store membership or painted content; sampled contiguous rows did not
prove the reported gap; no captured row exception established causation; the
silently empty reward renderer was reproduced but not tied to a measured
device gap. The emote-library virtualization gate is not a transcript
LegendList/Fabric validation.

## Transcript list, rows and banners

| Boundary | 31.6 / 31.6.2 | 31.6.1 | Result |
| --- | --- | --- | --- |
| ChatMessageList factory / Metro module | 4900 / 4896 | 4846 / 4842 | Different dependency registration |
| Inner list function | 22318 | 21887 | Older surrounding feature/prop set in .1 |
| LegendList factory / module | 4904 / 4900 | 4849 / 4845 | Equivalent normalized 401-function closure graph |
| Reset layout caches | 22388 | 21955 | Same normalized instructions |
| Update item positions | 22392 | 21959 | Same normalized instructions |
| Apply item size | 22418 | 21985 | Same normalized instructions |
| Row render callback | 38750 | 37689 | Per-row boundary absent in .1 |
| ChatLineComponent | 22068 | 21629 | Different notice/banner branches |

Normalization resolves string and object/literal references, closure pairing,
short/long operand encodings, branch destinations and string-switch tables.
The LegendList graph's closure edges were compared recursively, rather than
declaring equivalence from function names, matching string sets or omitted
closure IDs. This is static equivalence of those bodies and checked metadata,
not execution of measured native containers.

Both inner lists explicitly retain `estimatedItemSize: 36`,
`recycleItems: false`, `initialScrollAtEnd: true`, key/render callbacks,
draw distance and end-scroll maintenance. Neither explicitly turns on
`experimental_hideItemsUntilMeasured` in its list props. The internal optional
measurement/reveal machinery remains present. There is no discovered hotfix
to the three measurement functions or a change enabling recycling.

In 31.6 and 31.6.2 the row callback constructs
`ErrorBoundary(name=ChatLine, level=error, children=ChatLine(...))`, with no
explicit fallback. That boundary can return null after a caught row error.
31.6.1's callback constructs `ChatLine(...)` directly. Its older general
ErrorBoundary implementation also lacks the newer `renderFallback/reset`
option, but that does not add a substitute per-row boundary at this call site.
Removing this wrapper changes error containment; it is not evidence that an
underlying rendering exception or missing-message condition has been fixed.

31.6.1 also lacks this list's reader-resume focus plumbing, notice/held-message
callbacks, shoutout accent prop and the newer paused-footer message fields.
Its ChatLine dispatch has 51 string-switch cases versus 58 in 31.6, with
older/different inline-private-callout handling and no references here to
`CreatorGoalLine`, `EmoteLevelingChestShareLine`, `OneTapNoticeLine` or
`PowerCheerLine`. These are meaningful feature/banner differences relative to
31.6, consistent with the exact older bundle identity. They are not a new
fallback for ordinary messages or missing reward definitions. 31.6.2 restores
the 31.6 bodies exactly.

## Receipt, store, local echo and redemptions

| Path | 31.6 / .2 function | .1 function | Inspected behavior |
| --- | --- | --- | --- |
| Ordinary translated-line emission | 35388 | 34307 | Same null/nonce/emission control flow |
| Local-echo construction | 35303 | 34222 | Same sequence-based ID construction |
| IRC command/reward handling | 35931 | 34845 | Same command switches, including `custom-reward-id` |
| IRC reward callback | 35389 | 34308 | Same translation, reward tagging and emission |
| Translation | 35392 | 34311 | Same body flow; content-flag dependency slot 12 → 11 |
| Store `pushLine` | 45030 | 43496 | Same nonempty-ID deduplication and insertion flow |
| Nonce reconciliation callback | 48173 | 46537 | Same preservation of row key while replacing line ID |
| PubSub notice hook | 22060 | 21624 | Same two synthesized reward callbacks |
| PubSub callbacks | 38552 / 38553 | 37456 / 37457 | Same empty-body line construction/direct store route |
| `pushRewardRedemption` | 45065 | 43531 | Same blocked/restricted-user admission behavior |
| Reward renderer | 22089 | 21638 | Same reward lookup/body/deleted decisions |
| Reward snapshot map | 20059 | 18646 | Same automatic/custom definition indexing |
| Reward cache update | 20052 | 18639 | Same create/update/delete control flow |

Where instruction widths or string IDs differ, their resolved operands and
destinations were compared. Translation's changed dependency index resolves
the corresponding content-flag helper; it does not remove the null-translation
path. No new own-message retry, deduplication correction, nonce fix or forced
list membership was found at these boundaries.

The routes remain separate: IRC reward events translate/tag/emit, while the
PubSub reward/celebration callbacks create empty-body notices and invoke
`pushRewardRedemption` directly. The latter bypasses the ordinary translation
and emission methods. Store membership is still separate from successful
rendering.

Reward initialization/publication still derives `rewardsById` in `useChatData`
(21772 / 21369) from the settings snapshot map. Apollo/PubSub create/update/
delete processing remains a separate cache path. The snapshot builder and
cache-update body match after operand resolution. The surrounding .1 data hook
has fewer cheer-settings/cheer-data/toast fields, but the inspected reward
lookup does not acquire an unconditional placeholder or missing-definition
retry. Static comparison does not establish timely delivery or subscription
success on a device.

The actual donor factory and reward renderer, including their original child
bodies, were run against the same owned React/theme/Intl adapters:

| Controlled input | 31.6 | 31.6.1 | 31.6.2 |
| --- | --- | --- | --- |
| Empty or whitespace body, missing definition | null | null | null |
| Empty body, known definition | Notice | Notice | Notice |
| Nonempty body, missing definition | Message without reward header | Same | Same |
| Nonempty body, known definition | Notice + message | Same | Same |
| Deleted empty body | null | null | null |
| Deleted nonempty body | Message without reward header | Same | Same |
| Stable event, definition arrives then disappears | Notice appears then null | Same | Same |

Eight initial scenarios plus retained compiler-memo-cache arrival/loss checks
pass for every donor. The stable-cache check also confirms unchanged inputs
reuse the same rendered result. These tests exercise donor rendering decisions;
they do not simulate live PubSub, Apollo fetch completion, store delivery,
LegendList height measurement or painted pixels.

## Close/reopen and PiP lifecycle

The .1 chat-store cache functions corresponding to peek/acquire/release,
get-or-create and the store hook retain the baseline instructions (18707–18716
map to 18172–18181). The inspected connection-state hook, ordinary connection,
disconnect/dispose and hidden-state boundaries likewise retain the existing
logic after identity/encoding resolution. No new cache invalidation or
reopen-specific local-message recovery was found in these inspected JS paths.

31.6.2 has the exact baseline RN lifecycle bodies and framework text, so no
packaged RN or native-player code fix for PiP can be attributed to it here.
31.6.1's `twitch_rn_player` text differs; its PiP start/stop/restore delegates,
`pipRestoreDidFinish`, `appDidEnterBackground`, stream/source setters and
playback-state callbacks remain discoverable. The eight inspected PiP delegate/
entry methods retain their encodings and function lengths, as do the two
view lifecycle wrappers; this does not establish their complete callee graphs.
Their relocation is not proof
of a chat fix or full native semantic equivalence. Real presentation order,
chat mount/unmount, remote flags and state surviving PiP remain device checks.

## Five production Hermes stages

All five .2 target bodies, headers, Metro registrations, exports, registers,
branch destinations, original handlers, bytecode header fields and literal
buffers are **unchanged** because the complete HBC is identical to 31.6.
The unchanged production chain admits it naturally; no checksum, length or
exact-donor condition was changed or bypassed.

| Stage | 31.6 / .2 identity | .1 identity and impact | .1 classification |
| --- | --- | --- | --- |
| Width/layout | EmotePart 18563, 943 bytes, frame 41 | 19127, 947 bytes, frame 41; same normalized geometry; later literal instruction widens | Relocated/recompiled, semantically equivalent |
| Local echo | 35388, 121 bytes, frame 18 | 34307, 121 bytes, frame 18; same completed-line seam | Relocated/recompiled, semantically equivalent |
| Composer | 22516, 6,488 bytes, frame 100 | 22083, 6,240 bytes, frame 97; different props/branches/registers | Behavior changed; adaptation required |
| Popup/details | Factory 3694/module 3690, 600 bytes, frame 32 | Factory 3801/module 3797, 604 bytes, frame 32; equivalent normalized factory, relocated card/UI dependencies | Relocated/recompiled, semantically equivalent factory; bindings require adaptation |
| Strip/library | Factory 4924/module 4920, 336 bytes, frame 22 | Factory 4869/module 4865, 322 bytes, frame 22; different composer style slots and older autocomplete API | Behavior changed; adaptation required |

For .2 every stage is **unchanged and potentially reusable**, with additional
host structural/runtime validation below. This does not extend device support.

The .1 width registers remain ID r10, enlarged flag r11 and styles r13/r14;
the style insertion boundaries remain `0xd0`/`0x238`. Local null/nonce/emission
control flow is equivalent, but function/header/string identities move. The
.1 composer reads draft/channel/map into r49/r75/r47, ending that map read at
`0xa7`; 31.6 uses r51/r78/r49 and join `0xad`. Reusing frame-100 staging or
literal register operands would be unsafe.

Popup/export joins remain recognizable at `0x5e` and strip `0x46`, but module
identity is not the factory ID. Common React/RN/NativeModules/JSX bindings
remain 72/5/16/245; theme/sheet moves 2071 → 2118. Strip dependencies change,
including input 3459 → 3759, autocomplete 4676 → 4619, composer hook 4751 →
4687, settings 4937 → 4880 and library 4153 → 4174. The older autocomplete
surface includes `confirmHighlightedMatch`, already documented in the reverse
[31.6 port](TWITCH_31_6_COMPATIBILITY.md#module-bindings-and-changed-autocomplete-api).
It needs explicit adapter validation, not updated donor constants alone.

All five original target functions have no exception tables in these donors.
Any .1 graft would still need newly verified protected intervals, scratch/call
frames, relocation bounds, string/shape/literal references, full-header flags
and regenerated owned payloads. This investigation does not generate such a
port. Production admission correctly refuses .1 at width, with zero result
length and unchanged input; later stages are not reached.

## Native composer, legacy and WebP boundaries

Read-only metadata comparison covered 74 selected classes and 730 directly
declared instance/class methods per donor. Method sets and complete encodings
match. This does not validate inherited UIKit methods or runtime-initialized
Swift offsets; static zero offsets remain unresolved.

`React`, `hermesvm`, `ReactCodegen`, `ReactNativeDependencies`,
`twitch_rn_emote_input`, `twitch_rn_animated_image`, `FLAnimatedImage` and
`AmazonIVSPlayer` have identical executable text in all three packages.
Relevant preserved boundaries include:

- RN `RCTSource.data`, WebSocket delivery and native composer/attachment
  signatures and declared layout, including selection generation.
- `RCTImageLoader._loadURLRequest:progressBlock:completionBlock:` with
  encoding `@?40@0:8@16@?24@?32`, its native request/progress/cancellation
  boundary, and the unchanged RN image-view implementation.
- `RCTUIImageViewAnimated.calculateMaxBufferCount` (`v16@0:8`),
  `setMaxBufferCount:` (`v24@0:8Q16`) and `animatedImage` (`@16@0:8`).
- `FLAnimatedImage.initWithAnimatedGIFData:` (`@24@0:8@16`), the legacy
  ImageIO-adapter admission seam; native TWAnimatedImageLayer interfaces,
  attachment geometry/tap metadata and legacy ChatInput/palette declarations.
- The build-17 presented palette/coordinator named fields and `grabberTapped`
  (`v16@0:8`), preserving the investigated compact-detent seam.

31.6.1 reverses native layout declarations seen in the earlier 31.6 port:
`EmoteManager` size 448 → 320, `_graphQL` absent, `currentUserID` 408 → 280
and `recommendedEmotes` 416 → 288. The named eight-byte span used by Streamside
remains; hardcoded old offsets would not. `SkylineLiveChat` size 1138 → 1010
also loses `_graphQL`; two other inspected controller declarations lose that
field. Runtime-initialized field positions cannot be admitted from static
zeros. 31.6.2 restores the baseline declarations.

The build-14 ImageIO-backed adapter and build-15/16 legacy admission/read-ahead
are Streamside code, not code embedded in these donors. No changed donor image
loader/player ABI was found that requires replacing them. Provider-only
admission, original native image fallback, independent clocks, long frame
holds, cache budgets and request ownership still need their established
device checks after any packaging change. Native .1 ABI similarity cannot
compensate for its refused Hermes chain.

## Playback and VAFT

31.6.2 restores the exact baseline AmazonIVSPlayer, RN player, TwitchKit,
TwitchGraphQLAPI and other framework text. No new player/request implementation
was identified relative to 31.6 at those executable boundaries.

31.6.1 changes the RN player and generated GraphQL/native frameworks while
retaining the IVS engine text. Its `TwitchIVSPlayerView` declaration shrinks
480 → 440 bytes and loses `lowLatencyInitialBufferMs`, `onSeekCompleted`,
`onWarmPreloadLatency`, their setters/getters and RN prop configurations, plus
`player:didSeekToTime:`. These are actual native interface differences, not
only changed addresses. They concern buffering/seek/preload reporting; no
connection to transcript membership or the missing reward lookup is established.
31.6.2 restores the baseline player text and interfaces.

The inspected JS VOD/live token paths keep the
same token result/error handling and Usher URL construction. Live-token
functions 42517/41058 differ in register/environment layout and hoisting of
the same `mobile_player` default, not a newly observed token policy. VOD token
42536/41077, other token callbacks 44229/42749 and 47812/46185, and VOD Usher
builder 8642/8422 retain the resolved control flow. The inspected
`StreamAccessTokenQuery` still requests value, signature and authorization;
no new bypass or suppression conclusion follows from that.

Streamside's Foundation/AVFoundation interception is separate from Hermes
admission. No change here disables HLS interception or changes VAFT. Static
inspection cannot establish which live request path an account takes, server
manifest/ad markers, token expiry/retry behavior, ad suppression or clean-swap
recovery. No live ad-blocking acceptance is claimed for either supplied hotfix.

## Validation and reproducibility

Pinned host Hermes source: `40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c`.
The runner stamp, runner bytes and owned runner-source hash were verified.
The Hermes-98 parser uses the retained 40-byte full-header correction (flags
at byte 36); raw provisional parser offsets were not used as admission proof.
Native metadata inspection resolved chained-pointer formats 2 and 6.

The [optional regression utility](../../tools/investigate_hotfix_rewards.py)
requires the three exact IPA identities and validates their plist/HBC/footer,
Metro registration, reward export and renderer closure. It executes the
[owned fixture](../../tests/fixtures/rn_hotfix_reward_render.js) with dependency
IDs obtained from each donor registration. Only the temporary test global
bootstrap is substituted; donor renderer bodies remain unchanged.

```sh
python3 tools/investigate_hotfix_rewards.py \
  --baseline /private/tv.twitch-31.6.ipa \
  --hotfix1 /private/tv.twitch-31.6.1.ipa \
  --hotfix2 /private/tv.twitch-31.6.2.ipa \
  --hermesc /pinned/bin/hermesc \
  --runner /pinned/bin/streamside-snapshot-runner \
  --runtime-source /pinned/hermes --zig /path/to/zig
```

All three donor fixtures pass. The unchanged current production chain returns
the same five intermediate lengths for 31.6 and .2:
28,683,611 / 28,683,956 / 28,690,600 / 28,693,212 / 28,723,880 bytes.
These are temporary test-HBC results, not IPAs. .1 is refused unchanged.

The existing full-chain structural verifier also passes on the supplied .2 IPA:
deterministic owned-payload regeneration, bindings, 48,996 predecessor functions
at the final graft, 131 imported strip functions, original constants/handlers/
debug preservation and independent Hermes disassembly. The unchanged pinned
snapshot gate passes on its original HBC: 32 accepted snapshots and 7,344 emote
library window calculations, including the actual donor settings factory.
No admission check was weakened to run these checks.

No live UIKit/Fabric, real transcript measurement, server subscription,
background/PiP session, signer, playback or ad-bearing stream was tested.
Documentation validation passes for 75 Markdown files and 714 explicit
references; all 29 documentation-validator unit tests pass. The optional
utility also passes Python compilation. These checks do not expand the
runtime claims above.

## Recommended next step

Prefer **31.6.2** for the next candidate review. It appears to require donor/
packaging verification and device regression work, not a new five-stage RN
port. Keep exact admission and run the existing full checks before producing
that candidate. Do not implement a special .1 port merely to chase these gaps;
its older RN body would require explicit backward binding, composer and
autocomplete adaptation without resolving the reproduced redemption condition.

Device priorities are RN and legacy routing; ordinary own-message visibility;
known/missing-catalog redemptions through both routes; measured list membership
and zero/null rows; stream close/reopen and PiP restoration; all WebP surfaces
with fast and long-hold animations; then token renewal, HLS/ad-bearing playback
and swap/recovery. Keep controlled exceptions, disabled categories, retention
and rolling-trace coverage visible if the paused investigation is resumed.

**Verified:** supplied bundle identities, the static comparisons and controlled
host outcomes above. **Plausible:** catalog timing or a caught row exception
could contribute to invisible rows; the older .1 containment/feature surface
could change symptoms. **Unresolved:** the actual intermittent own-message/gap
cause, whether a null reward line reserves device space, and any upstream
runtime improvement not represented in these supplied static artifacts.
