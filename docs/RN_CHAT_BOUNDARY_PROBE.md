# Twitch 31.5 active chat boundary probe — build 51

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

`RN_CHAT_DIAGNOSTIC` defaults to zero. The source version is build 51; a probe
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
- Device activation, real hook hit counts, active bundle identity, and actual
  image/picker behavior remain unverified until the tester supplies reports.
