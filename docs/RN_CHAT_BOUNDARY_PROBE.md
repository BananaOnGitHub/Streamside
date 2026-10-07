# Twitch 31.5 active chat boundary probe — builds 51–53

This branch adds passive observation, not RN emote support. Build 50's earlier
device validation applies only to the legacy chat implementation still present
in the 31.5 binary. It is not evidence of compatibility with active RN chat.

## Branch model

| Branch | Role | Starting commit |
|---|---|---|
| `main` | Canonical development, no RN experiments | `5a0cda0` |
| `archive/twitch-31.5-build50-legacy-chat` | Exact preserved build-50 history | `3fbfa44` |
| `compat/twitch-31.5` | Eventual complete compatibility work | `3fbfa44` |
| `diagnostic/rn-chat-boundary` | Passive probe based on build 50 | `3fbfa44` plus this probe |

Build 50 is four commits ahead of main; main is its merge-base, with zero
main-only commits at probe creation. No existing archives or build46/build47
forensic branches are modified. No probe commit is merged into main or compat.

## Device evidence motivating this probe

Two build-50 reports from the same RN session show:

| Boundary | Before | After active chat and a native picker send |
|---|---:|---:|
| NSURLSession WebSocket callbacks/text | 23/23 | 34/34 |
| Tagged/room frames | 1/1 | 1/1 |
| Words scanned / provider matches / rewritten frames | 0/0/0 | 0/0/0 |
| Native data-source/transcript presentation callbacks | 0/0 | 0/0 |
| Old TextKit/attachment/layer counters | 0 | 0 |
| Old composer/picker/catalog counters | 0 | 0 |
| Provider registry global/channel entries | 124/63 | 124/63 |
| Provider image requests | 0 | 0 |

The earliest observed missing boundary is chat-message ingress, before provider
matching and image redirection. The eleven additional intercepted text frames
have no recorded attribution. Registry loading succeeded but there was no new
room fetch; the reports do not establish the tested channel's catalog. Zero
provider image requests do not establish a broken image redirect.

## Static donor evidence versus runtime evidence

Donor SHA256: `718762b71095c11754b1f58ad01fb580852414e6d7f468fbb2236b7c2419e641`.
The embedded Hermes v98 bundle has 27,786,480 bytes. The donor contains both
legacy and RN chat code, and HotUpdater; the actual running bundle may differ.

| Stage | Static 31.5 path | What this probe observes |
|---|---|---|
| Incoming transport | JS IRC client constructs a WebSocket; RN's default factory constructs SRWebSocket | IRC-host connect/open, actual delegate class, RCTWebSocketModule delivery |
| Native → JS | RCTWebSocketModule emits `websocketMessage` through RCTEventEmitter | Emission nested in the same IRC receive call; PRIVMSG/ROOMSTATE and nonempty emote-tag categories |
| Incoming tokenization | Hermes functions 18147/18143 parse chat/emote ranges; 18057 builds emote parts | No direct JS parser/token hook; ingress categories are evidence of delivery only |
| Own send/echo | JS send function 34208 uses buildLocalEcho 34222 and catalog map matcher 18157 | Outbound IRC PRIVMSG and input newline edits; neither proves echo/rendering |
| RN chat owner | React surfaces and consumed JS source bundle | Surface module names and bounded RCTSource.data fingerprints |
| Picker/composer | RN catalog maps feed TwitchEmoteInputView | Map setter counts and aggregate sizes, input value/change/layout, attachment geometry |
| Image loading | CoreImage uses RN Image; RCTImageLoader → RCTHTTPRequestHandler → NSURLSession | Loader/HTTP request counts, Twitch emote URL category, actual HTTP session/task classes |
| Image rendering | Fabric RCTImageComponentView / RCTUIImageViewAnimated | Image assignment and animation-start counters, result classes, view geometry categories |
| Animated decode | TwitchAnimatedImageDecoder | Decode entry count, original completion untouched |

Static Hermes function IDs apply to the embedded donor bundle only. Connect's
C++ options pointer and floating socket ID, attachment geometry struct return,
image decoder structs/floats, and observer pointers are forwarded with their
inspected ABI. All 28 hook signatures match the donor; runtime mismatches are
reported as `ABI-rejected` and are not hooked. Absent methods report `missing`.

Surface names identify registered entry modules, not the exact JS chat function.
The probe cannot prove which JS parser, token builder, local-echo function, or
picker action executed. That attribution is a later step once transport and
bundle ownership are established. RCTSource.data may be bypassed: no fingerprint
is not evidence that no bundle ran. Surface creation before probe installation
may also be missed. Hooks retry on application lifecycle notifications and
report collection.

## Passivity and privacy

Each wrapper calls its saved original exactly once, preserving arguments,
return values, error pointers, blocks and callback scheduling. No replacement
messages, emote definitions, catalog entries, image requests, geometry changes,
experiment flags or JS patches are introduced. Existing build-50 behavior is
left in place for comparison. The old animation forensic recorder is disabled.

The probe keeps aggregate counters, bounded class/module names, first native
caller image+offset, four weak bundle-data identities and bundle fingerprints.
IRC headers and URL categories are examined transiently; text, tags, channel/room
IDs, catalog contents, URLs, paths, headers and tokens are never retained.
Bundle hashing is capped at 64 MiB per body, with four weak identities; it does
not retain source bytes. FNV64 fingerprints identify bundles, not chat text, and
are not cryptographic integrity checks. Native caller image names use a fixed
allowlist, with other images reported as `other`.

Geometry counters observe all RN image views, not identified provider emotes.
RN chat's embedded EmotePart uses 24×24 inline and 56×56 enlarged geometry.
Future provider rendering must preserve variable widths in RN layout itself.
Legacy proportional ImageAttachmentLayer/TextKit handling cannot be assumed to
apply to this path. Rendering a provider image into an RN square is not success.

## Build and device procedure

```
RN_CHAT_DIAGNOSTIC=1 EMOTE_DIAGNOSTIC=0 ZIG=/path/to/zig ./build.sh
python3 tools/patch_ipa.py /path/to/decrypted-twitch-31.5.ipa \
  --framework build/Streamside.framework --output /path/to/probe.ipa
python3 tools/verify_ipa.py /path/to/probe.ipa --framework build/Streamside.framework
```

`RN_CHAT_DIAGNOSTIC` defaults to zero. The source version is build 53; a probe
IPA has an explicit `RN boundary probe (passive; this launch)` report section.

The procedure below is historical. Use the build-53 catalog/metadata procedure
at the end of this document for the next test; no send is required.

1. Install/sign the probe IPA and fully terminate then relaunch Twitch.
2. Enable Diagnostic Logging in Streamside settings. Copy report A before
   opening the test stream; autoplay traffic is acceptable and remains baseline.
3. Open an active RN chat, wait approximately 30–60 seconds for messages with
   native and provider emotes, open the new picker, select and send a native
   Twitch emote, and type/send a provider code if convenient.
4. Copy report B from the same launch. Do not clear counters or restart between
   reports. No legacy-renderer switch is requested or required.

For the first report, native Twitch emotes exercise image/decode paths even
though provider emotes still appear as text. Later RN rendering validation must
cover square, clearly wide, animated, and preferably animated-wide provider
emotes, including own echoes and incoming messages.

Positive IRC delivery + nested JS-event counts establish the suspected native
transport boundary for the observed session. Comparing these with still-zero
legacy ingress counters locates the bypass. Native image request counts and
result/view counters distinguish loading from rendering; cached results may
render without fresh HTTP requests. Picker map setter counts establish native
map handoff, not picker selection attribution. Keep installed/zero/missing/ABI
rejection distinct when interpreting reports.

## Completed host/build checks

- Existing 60 tests passed, plus the new passive probe test. The latter runs
  with address/undefined-behavior sanitizers and verifies unchanged receive/event
  objects, connect float/pointer forwarding, error-pointer/result preservation,
  exact wide geometry forwarding, header-only counting, oversized-frame refusal,
  ABI mismatch refusal and idempotent installation. These are host mocks, not
  actual iOS execution.
- All 28 donor Objective-C method encodings match the guarded hook specifications.
- Probe-enabled and probe-disabled arm64 iOS builds passed. Disabled framework
  contains no RN probe marker. Dylib/framework artifact guards passed.
- Patcher and `verify_ipa` passed. No donor entry was removed; only the main
  executable injection and app-name plist changed, and the two Streamside
  framework files were added. The embedded Hermes bundle and RN frameworks
  remain byte-identical. The older animation forensic recorder is absent.
- Output: `Twitch-31.5-Streamside-build51-rn-probe-unsigned.ipa`, 191,821,061 bytes.
  SHA256: `b55c11305d5a44c6216a4325575acf58c181c56d23f8c1f304595d731d9169a8`.
- Build-51 and build-52 device evidence is recorded below. Host checks alone
  do not establish actual iOS hook activity.


## Build 51 device results: same-launch reports A and B

Report A was supplied as a baseline; report B followed the RN chat test. These
are cumulative counters, not unique messages, views, images or catalog entries.
The reports alone do not establish the exact actions taken during B.

| Boundary | A | B | Supported conclusion |
|---|---:|---:|---|
| IRC connect/open/RN delegate/delivery | 0/0/0/0 | 2/2/2/27 | IRC-host SRWebSocket delivers to RCTWebSocketModule |
| IRC PRIVMSG/ROOMSTATE/emote-tagged PRIVMSG | 0/0/0 | 16/2/3 | Actual IRC chat and native emote metadata reached the RN receive hook |
| All JS socket events / nested IRC receive emissions | 8/0 | 248/27 | 27 websocketMessage emissions occurred inside observed IRC receives |
| Nested JS PRIVMSG/emote-tagged PRIVMSG | 0/0 | 16/3 | Native event emission carries the chat categories through the RN boundary |
| Old WebSocket text/tagged/room | 23/1/1 | 51/1/1 | Additional old-hook traffic is unattributed; old chat ingress did not become active |
| Old matching, rewrite, presentation, geometry, composer | 0 | 0 | All tested legacy integration boundaries remain idle |
| Global / channel registry | 110/63 | 124/63 | FFZ finished later; no new room fetch during the test |
| Nonempty input emote maps / cumulative entries | 0/0 | 2/1902 | RN's native composer receives catalog data; this is not JS local-echo map attribution |
| RN attachment geometry square/wide | 0/0 | 3/0 | Three native composer samples were square; no provider geometry validation |
| Twitch emote URL loader / HTTP requests | 0/0 | 592/579 | RN loads native Twitch emote images via a separate active pipeline |
| Fabric image deliveries | 63 | 403 | Fabric image rendering is active (all images, not just emotes) |
| Animated decoder entries / view start calls | 0/0 | 282/8 | RN animated-image decode and playback entry points are active |
| Outbound IRC PRIVMSG | 0 | 0 | Send/echo path remains unresolved; this hook cannot rule out alternate sends |
| Old surface constructor hits | 0 | 0 | Build 51 did not cover the actual surface construction path |

Observed classes are `RCTWebSocketModule`, `SRWebSocket`,
`twitch_rn_emote_input.TwitchEmoteInputView`,
`twitch_rn_emote_input.TwitchEmoteAttachment`, `RCTImageLoader`,
`RCTHTTPRequestHandler`, `__NSURLSessionLocal`, `__NSCFLocalDataTask`,
`RCTImageComponentView`, `RCTUIImageViewAnimated`, and
`TwitchAnimatedImageDecoder`. Installation status is separate from execution.

Both reports consumed an embedded Hermes-98 RCTSource body of 27,786,480 bytes,
FNV64 `3c748f1f3e33577c`. Recomputing the fingerprint on the supplied donor bundle
produces the same length/version/fingerprint. This ties static analysis to the
observed source body; it does not prove every static function executed. Two
bundle-load observations are two hooks in the loading chain, not proof of two
different bundles. No surface module name was captured.

The earliest demonstrated divergence is chat ingress:
`SRWebSocket → RCTWebSocketModule → websocketMessage emission toward JS` bypasses
the existing NSURLSession WebSocket chat rewrite. Provider matching and synthetic
ID generation were not exercised; the zero provider-image-request counters do
not implicate the registry or redirect. Catalog entries for a previously
observed room do not establish the active test stream's provider catalog.

`Last image result class: nil` can be overwritten by ordinary image clearing;
it is not a decode failure. The one HTTP completion error is not identified as
an emote request or provider failure. Image geometry counters include all RN
images, so their wide observations say nothing about provider proportions.

HLS independently recorded five ad-marked manifests and one clean alternate
swap with no token/HLS failures. Four ad-marked responses from a retired master
route were unmapped. This is separate from RN chat and is not changed here.

## Build 52: bridgeless surfaces, native JS scheduling and send attribution

This extends the passive probe; it does not implement RN provider rendering.
Build 51's 28 hooks remain. Sixteen additional guarded hooks cover:

| Added boundary | Observation | Limit |
|---|---|---|
| RCTHost.createSurfaceWithModuleName (both forms) | Registered module name; original mode/props forwarded | Does not read initial props or JS component internals |
| RCTFabricSurface init/start, hosting view window attachment | Module names including surfaces constructed through the bridgeless host | A surface created before installation can still be missed |
| RCTHost / RCTInstance.callFunctionOnJSModule and RCTCallableJSModules invocation | Fixed AppRegistry/runApplication and RCTDeviceEventEmitter/emit categories; websocketMessage argument category | Native scheduling, not a JS execution hook; nested boundaries can count the same call |
| RCTEventDispatcher.sendEvent | Fixed change/selection/submit/focus/blur/content-size event categories | All matching RN input events, not automatically chat-specific |
| RN input selection/begin/end and submit-block setter | Callback/wiring hit counts; original block untouched | Block installation does not prove block invocation; JS send-button path may bypass keyboard submission |
| SRWebSocket.send and sendData:error | Additional IRC PRIVMSG categories | Nested send methods may count the same message; no sender or text stored |
| RCTNetworking.buildRequest | Construction hits and first native caller | Request descriptor and completion passed unchanged; no callback wrapper |
| Existing RCTHTTPRequestHandler.sendRequest | Fixed GraphQL operationName categories for send, catalog and history | Counts request entry, not server acceptance or local echo; no response inspected |

Static donor React implementation at `0x2b32b4` shows
`RCTHost.createSurfaceWithModuleName:mode:initialProperties:` allocating a
`RCTFabricSurface` and invoking `initWithSurfacePresenter:moduleName:initialProperties:`
at `0x2b3334`. This is why build 52 adds these hooks instead of interpreting
build 51's zero legacy surface hits as no RN surface.

The donor has `SendChatMessage` (Hermes function 4608), `ChatEmoteSets` (3676),
`ChatEmoteUnlock` (4136), `ChatChannelLockedEmotes` (4183), and `ChatHistory` (3383)
operations. The JS IRC send function 34208 has an `onSendChatMessage` alternative
as well as an IRC send route. Function 43672 constructs a send input and invokes
`onSendChatMessageCallback`, handling GraphQL send results. These are static
candidates, not runtime-confirmed parser/echo callbacks. HTTP observation can
confirm the corresponding named operation at request entry without JS patching.
Persisted requests without operationName, other networking stacks, streamed
bodies and batches beyond limits remain unclassified.

Composer `setValue:` observations record empty/nonempty/other only. Map setters
record nil/dictionary/array/string/other shapes and at most 32 value-type samples
(string/number/dictionary/other) per call. They do not retain catalog keys,
emote IDs, codes, URLs, dimensions or messages. This distinguishes map shape
without asserting that it equals the JS IRC client's emoteTokenMap.

A 48-row rolling sequence retains only fixed category names and an ordinal:
surface, catalog-map, value-empty, value-nonempty, input-change,
input-selection, submit-event, IRC-send, GQL-send and GQL-catalog. It stores no
text, IDs, wall-clock timestamps or payload hashes. Sequence order is native
observation order, not proof of asynchronous JS execution order or causality.
Surface/map counters can repeat across nested constructors/setters.

HTTP request inspection is restricted to `gql.twitch.tv` `/gql` bodies at most
256 KiB, with at most 32 JSON batch operations inspected. Only exact fixed
operationName matches leave the function. Variables/query/headers/responses
are not read for attribution or retained; JSON parsing temporarily materializes
the existing request body. Original request/return/callback objects are not
replaced. No JS patches, runtime debugger/profiler activation, experiment
changes, emote definitions, provider fetches, synthetic IDs, redirects or sizing
changes are added. Direct JS parser/token/local-echo execution remains a gap;
these native hooks cannot honestly claim to observe it.

## Build 52 device procedure

Use one fresh launch and keep all four reports in that launch. The distinct
stages allow useful attribution even if the new event hooks are bypassed.

1. **A — before the test stream:** terminate/relaunch the installed build 52,
   enable diagnostics, and copy a baseline report. Autoplay traffic is allowed.
2. **B — incoming chat:** open a busy RN chat, receive native/provider emotes
   for 30–60 seconds, and copy a report before using the picker or typing.
3. **C — picker insertion:** open the RN picker and select one native Twitch
   emote into the composer. Do not send yet. Copy a report with the draft intact.
4. **D — sent message:** send that draft using Twitch's send button, wait a few
   seconds, and copy a report. Note whether your own message appears and whether
   its native emote renders. Optionally repeat with the keyboard send action in
   a fifth report, identifying it separately.

Do not switch renderers, restart, or clear counters between A–D. No provider
rendering is expected from this passive build. Supply just the diagnostic
reports and the observed send/echo behavior; no chat text or channel name is
needed. After the boundaries are identified, provider compatibility validation
must separately cover square, wide, animated and animated-wide examples in both
incoming and own messages. The legacy proportional machinery remains
unvalidated for RN.


## Build 52 completed validation and artifact

- All 61 host tests passed, including the expanded ASAN/UBSAN probe harness.
  New checks cover exact host surface mode/object forwarding, untouched JS and
  networking completion blocks/results, event and operation allowlists, catalog
  sample bounds, GraphQL body bounds, the rolling sequence bound, and absence of
  supplied private text in the report. Device observations are recorded below.
- All 44 guarded method encodings match the supplied donor's Objective-C metadata.
- Probe-disabled and probe-enabled arm64 iOS builds passed. The disabled build
  contains no build-52 probe marker. Framework and dylib artifact guards passed.
- Patcher and IPA verifier passed. Exact ZIP-entry comparison found only the
  existing app-name plist and main executable injection changed, two framework
  files added, and no files removed. Donor RN frameworks and Hermes bundle remain
  byte-identical. The old animation forensic recorder is absent.
- Output: `Twitch-31.5-Streamside-build52-rn-probe-unsigned.ipa`, 191,824,443 bytes.
  SHA256: `37c8c87c92856f9aca8df6d402d1caef31721298f66bedabd5052d88379a04d9`. Sign with the normal sideloading tool.
- Application integration sources (`TASEmotes`, `TASEmoteUI`,
  `TASEmotePresentation`, `SSComposer`, `Streamside`) are unchanged from build 51.
  Main, compat and the legacy archive remain at their original branch tips.

## Build 52 device results: staged reports A–D

These are cumulative reports from one launch. A is the baseline, B follows
incoming chat, C follows native picker insertion without sending, and D follows
the send-button test. The tester confirmed that their message appeared and its
native Twitch emote rendered. This establishes observed display, not whether
the message was optimistic, server-delivered, or reconciled between both.

| Observation | A | B | C | D |
|---|---:|---:|---:|---:|
| IRC receive deliveries | 0 | 303 | 626 | 880 |
| IRC PRIVMSG | 0 | 290 | 611 | 856 |
| Emote-tagged IRC PRIVMSG | 0 | 15 | 22 | 36 |
| Nested IRC websocketMessage emissions | 0 | 303 | 626 | 880 |
| Nonempty native composer map / cumulative entries | 0/0 | 1/951 | 1/951 | 1/951 |
| Empty/nonempty native input value assignments | 0/0 | 1/0 | 1/1 | 2/1 |
| Native composer square/wide attachment observations | 0/0 | 0/0 | 6/0 | 14/0 |
| HTTP SendChatMessage request entries | 0 | 0 | 0 | 1 |
| Outbound IRC PRIVMSG across observed send methods | 0 | 0 | 0 | 0 |
| Twitch emote URL loader/HTTP requests | 0/0 | 347/343 | 416/412 | 505/501 |
| Legacy matching/rewrite/presentation/composer activity | 0 | 0 | 0 | 0 |

The observed delegate is RCTWebSocketModule. A captures
`TwitchRNDiscoveryFeed` and `TwitchRNWarmup`; B adds `TwitchRNTheatre`, which
remains present in C and D. All reports fingerprint the same embedded
27,786,480-byte Hermes-98 source body, FNV64 `3c748f1f3e33577c`.

The composer emote map is a dictionary, with all 32 sampled values classified
as strings. The token-image map is an empty dictionary. No keys or values were
retained. B observes one request each for ChatEmoteSets,
ChatChannelLockedEmotes and ChatHistory. D adds one SendChatMessage request.
These operation counts do not establish response contents or server acceptance.

At D, the combined JS-scheduling socket-event count is 2,232 versus 1,116
socket events: the two scheduling boundaries each observe the same handoff.
This is not 2,232 unique events or evidence that JS executed twice. Likewise,
surface constructors and map setters can be nested or repeated.

RCTEventDispatcher.sendEvent remains zero despite native input focus and
selection callbacks executing. The current event probe does not observe the
active direct-block/Fabric input event route. Square attachment observations
are repeated bounds calls, not a count of distinct inserted emotes. General RN
image geometry/animation observations remain non-emote-specific.

The provider registry reaches 124 global and 63 room entries without a new room
fetch during the staged test. That does not establish the active RN stream's
provider catalog. Provider matching, synthetic metadata and provider image
redirection remain unexercised, so zero provider image requests do not identify
a redirect failure.

Local echo investigation is deliberately deferred. The next investigation
targets the catalog representation and incoming synthetic metadata path; see
[RN_EMOTE_REPRESENTATION.md](RN_EMOTE_REPRESENTATION.md). The initial findings
commit added documentation only; build 53 below adds the next passive test.

## Build 53: catalog identity and metadata consumer

Local echo remains deferred. Four new guarded hooks observe native input map
and template getters plus two Foundation URL construction boundaries. Existing
input setters/layout and incoming receive observers gain bounded structural
measurements. All 46 donor-defined encodings match the inspected binary; the
two Foundation hooks require their exact encoding at runtime.

| Measurement | Meaning | Limit |
|---|---|---|
| Per-input latest map snapshot | String/other key and value counts; decimal/opaque/URL/empty/oversize value shapes; distinct bounded nonempty strings and repeated values | Not picker row counts, alias provenance, collision counts or JS-store identity |
| Input surface scope | Fixed theatre/warmup/discovery/other categories from guarded hosting-view getters during layout | Can remain unobserved; not active-room or provider-registry attribution |
| Map/template getter hits | Native accessor execution and original returned object | Swift direct storage reads may bypass Objective-C accessors |
| Template categories | Unknown/default/static/animated/other CDN format | No actual template retained; setter traffic is not unique templates |
| Emote URL factory/init | Bounded Twitch v2 prefix classification; synchronous nesting inside native input updates and fixed caller-image category | Constructors can double-count; async or alternate Swift constructors can bypass attribution |
| Real incoming emote tag shapes | Decimal/opaque ID groups and numeric ordered/reversed/invalid range counts | No IDs, ranges or body retained; not JS parser, part mapper or rendering execution |

Catalog inspection is limited to four weak input identities, eight snapshots
per identity, 4,096 entries per dictionary and bounded string values. Sorting
uses transient pointers only; they are freed before returning. Reports retain
numeric snapshots, not codes, IDs, ID fingerprints or URL strings. Dead weak
slots are reusable and their previous snapshot statistics are discarded.
Incoming tag inspection has a 4,096-byte, 32-group, 64-range budget per PRIVMSG;
the shape observer is not a reimplementation of JS parsing or body validation.
Budget refusal counters must be considered before interpreting absent data.

The probe observes only authentic Twitch metadata. No synthetic tag, catalog
entry, URL replacement, callback wrapper, image redirect, sizing change or JS
patch is introduced. Exact catalog-ID overlap across callbacks is intentionally
not measured. These measurements test the structural ID/template contract;
they cannot establish synthetic-ID support or end-to-end provider rendering.

## Build 53 required device test

Sign/install the build-53 probe and fully terminate/relaunch Twitch. Keep
Diagnostic Logging enabled and collect these reports from the same launch,
without clearing counters between stages. No send or local-echo test is needed.

1. **A — baseline:** copy a report before entering the test stream.
2. **B — incoming:** open busy RN chat and wait 30–60 seconds for native Twitch
   emotes. Do not open the picker yet. Copy a report.
3. **C — picker insertion:** open the native picker, select one native Twitch
   emote and leave it unsent in the composer. Wait briefly, then copy a report.
   Note whether its composer image appeared.
4. **D — optional typed comparison:** clear the unsent draft and manually type
   a known native Twitch emote code. Leave it unsent and copy a report. Note
   whether it becomes an attachment. Do not record the code in the diagnostic.

Required evidence is the new build-53 section and its hook rows, together with
the existing bundle/surface/IRC/input/image sections. Compare latest map entries,
distinct/repeated values, value shapes and scope; template categories; map
getter execution; real incoming ID/range shapes; and URL construction nesting
between B and C. An installed-but-zero getter, unknown scope or zero nested URL
count is a probe limitation, not proof that the corresponding consumer is absent.
Provider emotes remaining text is expected. Do not change branches to implement
RN provider rendering until this passive evidence is reviewed.

## Build 53 completed validation and artifact

- All 61 host tests passed. The ASan/UBSan passive harness checks unchanged
  original arguments/results, map snapshot deduplication, exact forwarding of
  new getters/URL constructors, weak-slot capacity and reuse, snapshot/entry
  refusal, scope getter ABI rejection and positive theatre attribution,
  template/URL categories, header-only range counting and overflow refusal,
  and report privacy. Host mocks do not establish iOS runtime activity.
- All 46 donor-defined hook encodings match; two Foundation methods remain
  runtime-guarded. Enabled and disabled arm64 iOS builds and both artifact
  guards passed. Disabled binaries contain no RN probe report markers.
- IPA patching and verification passed. No donor entry was removed. Only the
  main executable and app-name plist changed; two Streamside framework files
  were added. Every other donor entry, including the Hermes bundle and RN
  frameworks, is byte-identical. The old animation forensic report is absent.
- Output: `Twitch-31.5-Streamside-build53-rn-probe-unsigned.ipa`, 191,827,729 bytes.
  SHA256: `5ce83e576f314d73e3e2956c37eeff315631e8e50ea74f1af18b2d3b24677fa0`.
  Sign with the normal sideloading tool. Device results are summarized in
  [RN_BUILD53_FINDINGS.md](RN_BUILD53_FINDINGS.md).
- This work stays on `diagnostic/rn-chat-boundary`; main, compat and the legacy
  archive are unchanged. The initial approval block was resolved: the findings
  and tested build-53 tree were published at
  `423858b9d042215b954326359ec081114eb77adb`.

## Build 54: native attachment and scoped paragraph consumers

Build 53's recorded map is 951 string-token/string-ID entries, including 921
distinct bounded values and 30 repetitions. Native picker insertion reaches
the composer value/attachment bounds boundary, while map/template getters and
input-attributed URL construction remain uninformative. See
[RN_BUILD53_FINDINGS.md](RN_BUILD53_FINDINGS.md) for staged A–C evidence and
Knoks's complementary, separately observed paragraph render hierarchy.

Build 54 adds six hooks (54 total), without RN implementation changes:

| Boundary | Measurement | Limit |
|---|---|---|
| Native TwitchEmoteAttachment `initWithData:ofType:` | Native returned attachment and synchronous input nesting | Swift initializers may bypass Objective-C entry |
| NSTextAttachment base `initWithData:ofType:` | Same native-class filter, including superclass dispatch | Can double-count with subclass hook; unrelated attachments only forward |
| NSTextAttachment `setImage:` | Native composer attachment assignments: nil/UIImage/TwitchAnimatedImage/other | No request provenance, completion replacement or unique attachment identity |
| Existing native attachment bounds | Guarded image getter categories and source-image square/wide categories | Bounds calls repeat; image geometry is intrinsic source geometry, not rendered width |
| RCTParagraphComponentView `updateState:oldState:` and `layoutSubviews` | Scoped callbacks, then guarded attributed-text reads | Opaque C++ references are passed through unchanged, never decoded |
| RCTParagraphComponentView `attributedText` | Original return plus scoped structural sampling; observer reads counted separately | Nil/other/unavailable getter is an observation gap; not proof of absent rendered text |

The four new donor-defined encodings are checked against the supplied Twitch
31.5 donor; `tools/verify_rn_hook_abi.py <Twitch.app>` verifies all 50
donor-defined hooks. The four Foundation hooks (two URLs, two attachment methods)
remain exact-ABI runtime guarded, not donor-verified. Base hook call rows count
all receivers; the new native attachment counters apply only to the native
composer attachment class. Every original is invoked exactly once with the same
arguments/result. No Swift offsets, descriptions or private state layout are read.

Paragraph observation is main-thread-only and requires BOTH a message marker
(`chat-message-line`, `chat-message-pressable`, or `chat-message-row`) AND a
chat-region marker (`chat-message-list`, `chat-message-region`, or `chat-area`)
among the view and at most 63 ancestors. Identifiers are transient bounded exact
comparisons, not retained. State updates may precede mounting, so unscoped state
callbacks are expected; layout provides another observation opportunity. No
accessibility label, attributed-string text or arbitrary attribute dictionary is
read. Only the `NSAttachment` attribute is queried across bounded runs.

Sampling is capped at 512 attempts per launch, 4,096 UTF-16 units per attributed
string, and 256 attribute runs per sample. Attempts include nil/empty/refused
reads. Once exhausted, observer-created getter reads stop; naturally occurring
getter calls still forward. Every refusal has a counter. Attribute ranges are
checked for progress, bounds and overflow then discarded. Native-composer,
other NSTextAttachment, and invalid-object runs are separate. **Other attachments
are not necessarily emotes.** Runs and callbacks are repeated observations, not
message, unique-emote or delivery counts. No ID, token, URL, text, image data,
attachment identity, C++ state or payload survives observation.

This targets two consumers without assuming they share the same representation.
Even a positive paragraph attachment result will not establish JS parser/token
execution, synthetic metadata compatibility, a complete KMP message model,
provider rendering, or local echo. No provider injection, catalog mutation,
request redirect, geometry change, callback replacement or JS patch is added.

## Build 54 required device test

Sign/install build 54, fully terminate/relaunch Twitch, and keep Diagnostic
Logging enabled. Collect reports from the same launch without clearing counters:

1. **A — baseline:** before entering the test stream, copy a report.
2. **B — incoming:** open busy RN chat; allow native Twitch emotes to appear for
   30–60 seconds without opening the picker, then copy a report.
3. **C — native picker:** select one native Twitch emote; leave it UNSENT,
   wait briefly, and copy a report. Note whether its composer image appeared.
4. **D — optional typed comparison:** clear the unsent draft, type a known
   native emote code, leave it unsent, and copy a report. Note whether it became
   an attachment. Do not include the code in the report.

The new build-54 section and hook rows are required, alongside the existing
catalog/template/incoming-tag sections. Compare B→C native attachment init,
image assignment and bounds-image observations. For incoming paragraphs, compare
scoped state/layout/getter counts, nil/empty/other samples, attachment categories,
and refusal counters. Preserve the distinction between observer-generated reads
and natural getter traffic. An installed-but-zero hook or missing scope is not
evidence that image loading or chat rendering failed. No send or local-echo test.

## Build 54 completed validation and artifact

- All 61 host tests passed, including the expanded ASan/UBSan RN harness:
  initializer replacement-object forwarding, unchanged unrelated base receiver
  calls, image category filtering, parent/region scope gating, main-thread skips,
  untouched opaque state pointers, original getter results, observer-read
  separation, nil/other/empty values, getter/attribute ABI refusals, length/run/
  sample limits, zero-progress range rejection, privacy and worst-width report
  tail retention. The report buffer is 32 KiB; host mocks do not prove iOS activity.
- `verify_rn_hook_abi.py` matched all 50 donor-defined encodings. Four Foundation
  hooks remain runtime-only. Enabled and disabled arm64 iOS dylib/framework
  builds passed. Disabled outputs contain no RN probe report markers.
- IPA patching, artifact guards and unsigned IPA verification passed. No donor
  entry was removed. Only the main executable and app-name plist changed; the
  two Streamside framework files were added. Every other donor entry, including
  React/native input frameworks and the embedded Hermes bundle, is byte-identical.
  No old emote animation forensic recorder was enabled.
- Output: `Twitch-31.5-Streamside-build54-rn-probe-unsigned.ipa`, 191,830,143 bytes.
  SHA256: `fabe23ceef95d5e6ca3140d9a2b9545f63b0196abee62c0e6d429fae8de52009`.
  Sign with the normal sideloading tool. The A–C device test above is required.
- Changes are isolated to the diagnostic probe, report/version metadata,
  linker stub, tests, ABI-checking tool and documentation. Local echo remains
  deferred; existing application integration sources are unchanged.
