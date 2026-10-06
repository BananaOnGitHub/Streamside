# Twitch 31.5 active chat boundary probe — builds 51–52

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

`RN_CHAT_DIAGNOSTIC` defaults to zero. The source version is build 52; a probe
IPA has an explicit `RN boundary probe (passive; this launch)` report section.

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
- Build-51 device evidence is recorded below. Build-52 device behavior remains
  pending; host checks do not establish actual iOS hook activity.


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
  supplied private text in the report. Actual device execution remains pending.
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
