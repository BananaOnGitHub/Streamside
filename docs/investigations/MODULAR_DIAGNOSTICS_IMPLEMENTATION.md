# Modular diagnostics implementation

Implementation branch: `feat/modular-diagnostic-runtime`, based on
`0a3cf9603f8885d6c2d8433dded227698b047f20` from `dev/3.1.0`.
The historical chat and composer diagnostic branches remain unchanged.
The initial target is exact Twitch 31.6.2 build `262872150334984303`, Hermes 98.
This is active implementation evidence, not device acceptance.

## Checkpoint A: coordinator and immutable registry

The native [core](../../src/TASInvestigation.c) supplies fixed version-1
descriptors for current chat snapshots, chat lifecycle, and reward observation.
Its asynchronous command coordinator keeps pending commands separate from
acknowledged Armed state, rejects stale generations/sequences, invalidates
failed/timed-out commands, and does not expire an acknowledged armed session.
No timers, bridge calls or instrumentation are installed by this core.
Missing runtime admission remains Unsupported. No UI or live adapter exists
at this checkpoint; the core alone cannot activate an investigation.

The allocation-free native JSON reader bounds input to 16 KiB, 256 tokens,
eight nesting levels and 256 UTF-8 bytes per string. It validates UTF-8 and
surrogate pairs, rejects decoded duplicate/unknown keys, integer overflow,
fractional/exponent spellings, incompatible versions/profiles, new event
families and resource expansion. Failed parse clears the output. Remote
configuration cannot introduce executable code, hook locations, selectors,
property paths or transport endpoints. General diagnostic presets are separate.

The [bundled manifest](../../diagnostics/investigations/rn-chat-gaps/1.json)
selects event-driven observation in the first prototype, separate 256/64 event
rings, two current lists, 128 snapshot entries, a 2-second snapshot deadline,
bounded work/rate/identity budgets, and return to Armed after capture.
These are compiled ceilings and manifest choices, not measured device results.
Observation and retention are implemented in later checkpoints.

The exact manifest bytes and SHA-256 pin are generated into a checked-in header.
The host must supply the system cryptographic primitive. An invalid optional
cache is rejected in favor of the separately verified bundle. Only identical
compiled bytes can be accepted from a cache; mutable signed updates and actual
network/disk-cache transport remain unimplemented. The registry index and schema
are authoring artifacts; native validation is the runtime admission authority.

Validation: 12 focused native tests passed, including every manifest truncation,
wrong native/Hermes identities, missing capability readiness, escaped duplicate
keys, narrowed budgets, integrity fallback, late activation, 100 repeated
arm/capture/stop cycles and stale acknowledgments. Ordinary native artifacts
passed verification; the complete host suite ran 205 tests: 201 passed and four
Apple/donor-runtime cases skipped before the new Hermes toolchain was used.
These results do not establish live RN command delivery or device overhead.

The local baseline record is committed as `962aef7`. Local commits use the
explicit agent identity `Codex <codex@localhost>` because a personal Git author
identity is not configured. No global Git settings or remote refs are changed.

## Next validation boundary

The exact pinned Hermes compiler and existing runner have been built locally.
The original donor bundle and React framework are extracted once under the
workspace donor directory. The native-to-JS seam, dormant list attachment,
original callback preservation and real donor accessors still require admission
and executable validation before claiming a working runtime.


## Checkpoint B: dormant scoped seam and callable commands

Checkpoint A is committed as `642adce`. The scoped Hermes graft supports two
exact predecessors: the unchanged original donor when functional emotes are off,
and the complete existing five-stage chain when they are on. SHA-256 and footer
admission reject modified, partial or duplicate predecessors.

Factory 4900 receives one additional environment slot for an owned list-creation
adapter. Its original memoized `ChatMessageList` export remains identical. The
original list JSX call in function 22318 supplies its store as the adapter's
execution context; the adapter preserves the original component type and props,
forwards callback/object refs and cleanup/error identity, and retains at most
two mounted handles. It adds no React hooks or components and does not modify
shared JSX exports. Existing short branches in that function are widened and
relocated; other function bodies and original literal/string storage remain
unchanged. No donor function body is generated into repository headers.

The native donor audit finds `RCTBridgeModuleDecorator.attachInteropAPIsToModule:`
calling `setCallableJSModules:` conditionally. The injected callable object has
`invokeModule:method:withArgs:onComplete:` encoding
`v48@0:8@16@24@32@?40`; its actual donor body invokes the retained bridgeless
scheduler block. This is the native counterpart to React Native's documented
[callable-module API](https://github.com/react/react-native/blob/main/packages/react-native/React/Base/RCTBridgeModule.h).
The original candidate `RCTInstance._attachBridgelessAPIsToModule:` does not
inject that property in this donor; the module decorator is the verified seam.
Native evidence is in local `build/investigation-native-channel.json`.

The native host verifies Twitch/main, React and Hermes UUID/text fingerprints,
version/build and actual callable-method ABI before registering its independent
module. It uses weak module/callable handles and a startup ping/ack through the
normal RN scheduler. Actual activation requires the round trip, not merely
setter availability. There is no arbitrary source evaluation, unchecked JSI
entry or command polling. One coalesced main-queue update owns at most one
command/probe deadline timer; it is removed while no command is pending.

The compiled Hermes gate passed both original and functional predecessors:
owned bootstrap, actual donor factory/export join, late callable command with
no intervening render, callback/object-ref forwarding, cleanup return/context,
original exception identity and 100 registration/teardown cycles. Structural
checks cover 206 relocated branches, handler boundaries, imported closures,
original string/literal storage and all unrelated function bodies. Native
artifacts passed verification; the suite ran 205 tests: 201 passed, four skipped.
The earlier existing Hermes library gate also passed 32 native-accepted snapshots
and 7,344 window calculations before the host integration changed its inputs.

Checkpoint B deliberately advertises zero ready observation capabilities.
The UI remains Unsupported until the recorder and snapshot adapters are added.
Live iOS scheduling, native weak lifetimes and dormant overhead still need device
acceptance. Linux's callable facade proves owned command handling and bytecode
execution; it does not execute RCT/UIKit or establish device performance.

The native invocation IMP must also belong to the admitted React image at its
verified offset; a later foreign method replacement disables delivery.

## Checkpoint C — bounded event history and numeric transport

The fixed adapter now retains up to 256 ordinary and 64 priority records in
separate rings. Shared token admission precedes alias allocation and event
formatting; monotonic work accounting enforces a 10 ms/s admission budget and
2 ms callback ceiling. Counters saturate. The observer does not bridge events
while armed, and has no armed timer or session expiry. Exact original calls,
returns, exceptions and context are retained. Scoped store subscriptions and
owned method descriptors are released on Stop; foreign replacements survive.
There are at most 16 hook records and two mounted scope records.

Translation, emission, unpublished local-echo emission, aggregate store changes,
IRC rewards, direct store reward insertion and mounted-list lifecycle have
compiled adapters. Missing observations do not establish filtering, dropped
messages, reconciliation or server acknowledgments. Reward renderer/catalog,
layout and native geometry are not yet admitted. A coverage mask records the
methods actually installed. Alias entries/bytes and object associations have
independent bounds; no private identity is serialized.

Capture freezes the event rings before its first numeric-only bridge transfer.
The native parser rejects strings, objects, nonintegers, wrong columns, extra
data, oversize packets, reordered/duplicate/stale parts and excessive transfer
rate. It retains one bounded frozen report, including partial reports on error.
Capture/Stop generation checks cancel late work. The native host sends a fixed
best-effort Stop on failed/expired commands; it never enters a blocked JS queue
through an alternative path. Captures have a three-second native cooldown.

Compiled Hermes acceptance passed both original and functional predecessors:
late arm without rendering, over two hours of simulated armed time, ordinary
saturation with independent priority capacity, numeric privacy sentinels,
known-size/list correlation, failed reads, cancelled capture and 100 teardown
cycles. Native cross-build/receipt verification passed. These are host tests,
not on-device timing/CPU/keyboard acceptance. Snapshot code is present for
fixture coverage, but snapshot capability remains unadvertised until the donor
getter audit and mutation traps pass in checkpoint D.

## Checkpoint D — exact donor getter audit and safe current-state capture

Snapshot capability is enabled after executing donor getter 38870, content-size
helper 22335, its content-inset dependency 22334, velocity helper 22458, and
positionAtIndex 46258 in pinned compiled Hermes. Eight horizontal/RTL/inset
combinations ran behind deep Proxy mutation traps, including original data,
positions, idCache, props, scroll history and sizes. No donor state changed.
The inset helper copies into a new object; it does not mutate source props.
The velocity helper reads history; donor updateScroll 22370 trims that history
to five elements (0xf9–0x10b). Neither elementAtIndex nor sizeAtIndex is called.
The validation receipt fingerprints these exact donor bodies.

The snapshot correlates bounded store and committed list membership using arm
labels, and includes safe known sizes, positions and viewport values. Unknown
sizes remain -1; unavailable geometry, renderer/catalog, estimated sizes and
confirmed reconciliation are explicit. Store revision is read before/after;
changed, unavailable, budget-limited and transfer-truncated flags are distinct.
No functional store/list setter, renderer or layout operation is invoked.
Per-entry deadline checks bound current reads to the smaller of 2 ms callback
work and the total JS budget; fixed donor getters themselves cannot be
preempted. First frozen-history transfer precedes these current reads.

The deeper donor audit found and corrected checkpoint B's r39 store assumption:
ChatMessageListInner reuses r39 for an onScroll callback before the JSX seam.
The adapter now reloads the original store from its existing environment
(r41, slot 0) into dead scratch r37. A compiled test executes the actual patched
seam bytes with poisoned r39, proving the retained store binding, one original
JSX call, and correct dormant fallback. Registers 36/37/41 are unused after
the seam; branch relocation and all unaffected functions remain verified.
This correction is preserved here rather than rewriting checkpoint B history.

## Checkpoint E — native controls and development candidate

The independent Diagnostics → Investigations page exposes actual state,
Arm, Capture Snapshot, Stop, an optional in-chat Capture button, and explicit
copy/share of the one retained numeric report. No preset change or chat reopen
is requested. The button is a fixed native control added to the page's existing
app window: no new key window, safe-area change, focus command, React insertion
or transcript layout operation. It requests capture before changing its own
title and never opens reporting UI automatically. Only the button's rectangle
accepts its touches. Orientation positioning uses the native autoresizing mask.
Background notification requests Stop and removes the button. Commands and
acks update the page through the main queue, without an armed polling timer.
Keyboard, accessibility, hit testing and rotation still require device checks.

Registry revision 2 narrows the selected event families to actual compiled
adapters; revision 1 stays historical. The shipped report names remaining
coverage gaps, partial sampling and unknown sizes. A direct reward-store call
does not independently prove PubSub provenance. Native export retains only
numeric columns, not the wire string. Copy/share is explicitly user triggered;
there is no upload or persistent automatic report file.

The ordinary build now refuses stale/missing compiled runtime evidence. The
committed receipt fingerprints production native/JS/graft inputs, patch-chain
payloads, registry, runner source and executable fixtures. It records actual
pinned donor/Hermes replay, while allowing a clean CI build to check that
recorded proof without distributing the donor. A receipt is not a signature or
device attestation. Refreshing it requires the exact donor and toolchain.

Candidate identity is 3.1.0-build.19, separate from the historical build.18
baseline. Public feature/release documentation remains at its maintained
release scope until feature freeze; these development findings own the trial.

### Final local validation

The full suite ran 210 tests: 208 passed and the two Apple-only integration
checks (Foundation and ImageIO) skipped on WSL. Exact donor settings binding
and the compiled Hermes virtualization pipeline ran with all required inputs.
The new investigation gate passed both original and functional predecessors,
including deep donor getter mutation traps and the actual scoped JSX seam.
The production native report parser receives the compiled recorder's packets
through the host fixture, including a fully occupied eight-batch capture with
both ordinary and priority rings saturated. A full final batch is distinguished
from actual transfer truncation. Missing, stale and incomplete build receipts
are rejected. Both parsers survived 20,000 malformed inputs each under Address
and Undefined Behavior sanitizers. Native Mach-O, framework receipts and
documentation/version checks passed.

This is a device-test development candidate, not device acceptance. Still
required: install/sign on the intended iOS device; establish the real RCT
startup round-trip; arm after chat has already mounted; remain armed during
a normal long session; capture without leaving the stream or dismissing the
keyboard; check focus, scrolling, accessibility, overlay hit testing and
rotation; reproduce ordinary/own/reward scenarios; repeat capture/Stop and
background/foreground cycles; inspect the exported numeric report. No
Apple/device performance or compatibility pass is claimed from host results.

### Packaged candidate identity

Source candidate: `f9bcc5867588edd75a53bf48b4eaa9d4b24e1bdc` (`feat/modular-diagnostic-runtime`).
The unsigned device-test IPA was generated and `verify_ipa.py` passed against
the exact build receipt. The packaged framework is byte-for-byte identical to
the verified local artifact. The donor HBC remains unchanged in the archive;
the admitted graft occurs at runtime. Main, React and Hermes UUIDs and text
digests in the packaged IPA still match the strict native admission profile.

- IPA SHA-256: `07cec35926960ce80badf3ff29b6f66db4c9c5b0450bf73a121cd17befa80db5`.
- Framework binary SHA-256: `4c18f14dd1ee43a5d0d5f9792a8617819be03f6b70f3ee13ef15bd408342c9ad`.
- Dylib SHA-256: `e8b8e77b1ea58eba428cbdce46b5aa6a800c646eb7fdcb1e229adbbf486f3af1`.

The IPA, checksum, structured validation record and device-testing handoff are
under the local Streamside workspace's `artifacts/` directory, outside Git.
The candidate requires signing before installation. No device run, release,
push, merge or publication was performed. Coverage masks record adapters
installed during an arm session, not proof of complete observation of every
scope; missing observations remain inconclusive.

## Build 20 — startup ordering and device failure evidence

Device feedback for build 19 confirms ordinary Twitch chat works while the
Investigations controls remain Unsupported after Refresh Status and stream
changes. The copied report identifies exact Twitch 31.6.2 build
262872150334984303 and all six existing functional RN admission flags are 1.
This excludes a simple failure of the existing source/functional patch chain;
it does not prove the separate investigation graft or native admission passed.
Build 19 omitted investigation startup state from that report, so the device's
exact failed stage remains undetermined. Chat/composer visibility is not an
admission input. No off-screen-layout diagnosis is claimed.

One startup ordering defect is reproduced and corrected: native `ready` used
to return zero if callableJSModules had not arrived, permanently leaving the
JS epoch at zero. Now `ready` can bind the verified source/ABI first and retain
its dormant scope-registration seam. Arrival of the exact admitted callable
triggers one startup probe. Callable-first and ready-first order both work;
the coordinator remains Unsupported until the probe ACK. No timer polls,
arbitrary JS entry, capability bypass, activation or chat remount is added.
Queued probes carry their source epoch; stale/expired probes and acknowledgments
before a probe has been scheduled do not admit the runtime.

Native startup records fixed numeric stages, profile checks, source/graft
admission, API availability, ready attempts, callable availability and probe
state. These are available through Copy Runtime Status even without a capture,
and in the General diagnostic report independently of the selected preset.
The copied fingerprints are executable UUIDs/text digests, not chat/room/user
identities. JS reports one bounded startup mask; bootstrap exceptions become
code 256 and never include exception text. All startup counters saturate.

Native stage: 1 registry, 2 native profile, 3 callable ABI, 4 callable owner,
5 registration API, 6 allocation, 7 class setup, 8 registered. Profile bits:
1 dyld APIs, 2 declared donor metadata, 4 main parsed, 8 React parsed, 16 Hermes
parsed, 32 main/Hermes identity match, 64 React UUID, 128 React text digest.
Source stages: 0 missing hook, 1 installed, 2 observed, 3 graft admitted,
4 graft refused. Startup-mask bits: 1 ready, 2 ack, 4 report, 8 JSX,
16 callable registration, 32 WeakMap, 64 Map, 128 monotonic clock; 256 exception.
Ready-result 1 is rejected; 2 is accepted while awaiting verified round-trip.

Validation includes the production native ready/setter/probe/ACK functions in
a host Objective-C lifetime facade, both dependency orders, wrong API/caps,
missing donor readiness, foreign callable class, duplicate ready, premature
ACK, source replacement and expired queued probes. Compiled Hermes executes
the new missing-API and exception paths on both exact predecessors. This
reproduces the ordering defect in host tests; it does not establish that the
ordering defect caused the reported device failure. Build 20 must be tested
on the device, with its copied startup status if Unsupported persists.

The handshake watchdog is scheduled when ready is accepted, including when
the callable has not arrived. Thus absence of the dependency cannot leave an
unwatched pending handshake. This remains a one-shot startup deadline; it is
cancelled after the acknowledgment and adds no armed-session polling.

Build-20 local validation: 211 tests ran, 209 passed and two Apple-only checks
skipped (Foundation and ImageIO). Exact donor/Hermes validation passed both
predecessors, including startup failure masks, getter mutation traps, the scoped
list seam, saturated recorder/capture transport and teardown. Native artifacts,
receipt freshness and documentation/version checks passed. Live iOS scheduling
and resolution of the reported failure still require the next device run.

Build-20 candidate source: `5d8f165293ff14f45d0bb072a0177c2fdf9b4336`.
The unsigned IPA passed package verification; its framework bytes match the
verified receipt, its original donor HBC is unchanged, and all three donor
UUID/text identities still match the admission profile.

- IPA SHA-256: `17693badb7685abca0435356ef9e5f95b873103bea322f1d13058f815c544378`.
- Framework binary SHA-256: `1bca6ed167ad16cc849fca1f65b834ab7e0b4b165829e60569b8d5c92aa229f5`.

The workspace artifacts directory contains the IPA, checksum,
`build20-validation.json` and `BUILD20_TESTING.md`. Build 19 remains intact.
The next device result should include Copy Runtime Status if Unsupported
persists; no claim of resolved device startup is made before that test.


## Build 21: standard global binding after build-20 device failure

Build 20 remained Unsupported on the device. Its copied status reports native=1,
native-stage=8, profile-bits=255, source-stage=3, epoch=1, startup-mask=256,
startup-calls=1, ready-calls=0 and ready-result=0. Thus native compatibility,
module registration and the source graft passed. The JS installer caught an
exception before its first API-availability report or native ready call. The
build-20 dependency-order correction did not resolve this device failure.
Chat/composer visibility is not a readiness input and does not explain this result.

The installer used the free identifier `global`. This exact donor's top-level
bootstrap selects `globalThis` first and supplies that object to Metro factories;
it does not establish a legacy `global` alias. The donor's other `global`
property uses are library object fields, not a global-object alias assignment.
The owned installer bypasses Metro's normal parameter binding, so it cannot rely
on the module-local name used in React Native source. The old host fixture
declared `var global=_runtimeGlobal`, masking that dependency.

The unchanged build-20 production graft was executed in the pinned Hermes-98
runner with all expected APIs installed on the actual global object and without
that fixture alias. It returned null, reported exactly one startup mask of 256,
and made zero ready calls: the same boundary observed on the device. No native
signature, profile or capability check was weakened to obtain that reproduction.

Build 21 uses the standard `globalThis` binding for callable registration,
the monotonic clock and capture timers. The bootstrap and recorder fixtures no
longer install the legacy alias and assert that it is absent. The compiled
acceptance gate runs the actual owned installer and the modified donor factory
in this environment for both original and complete functional predecessors.
Existing startup-order, failure-path, dormant-work, ref identity, recorder and
transport checks remain applicable. Actual iOS confirmation remains pending;
matching a host failure signature does not establish successful device startup.

Build-21 local validation: all 211 tests completed, with 209 passing and the
two Apple-only Foundation/ImageIO checks skipped. Both compiled Hermes
predecessors, native framework verification and documentation checks passed.
The candidate retains the same strict donor identity and verified startup ACK
requirements. Build-20 artifacts and their original records remain preserved.

Build-21 candidate source: `2ccd4ed6fed1cd8fa1febd605998d63f72887e45`.
The unsigned IPA passed package verification. The packaged framework exactly
matches the verified native build; original donor HBC and all three native
UUID/text identities remain unchanged.

- IPA SHA-256: `95063dae49543302df8288f52049f3469499248b862c6bcf503db439f381f3b4`.
- Framework SHA-256: `30ba38969ef1a32bae0bad022bbcc7a87c83ca69bbf4e03bbdf33bf29e45077d`.

The workspace artifacts directory contains the distinct build-21 IPA, checksum,
`build21-validation.json` and `BUILD21_TESTING.md`. Device confirmation is pending.


## Build 22: capture action survives settings dismissal

Device feedback for build 21 confirms Dormant/Armed transitions work. The
pre-ready startup failure is therefore resolved on the reported device.
The user-enabled Capture button appeared over settings but was absent after
returning to chat. Capture transport, focus and keyboard behavior have not yet
been confirmed by this feedback.

Checkpoint E attached the button directly to the settings page's existing
window. It had no independent presentation ownership across that window's
content/presentation changes. Build 22 gives the opt-in action an owned native
window bound to that same UIWindowScene. Its controller/button do not belong
to the settings page hierarchy, so dismissal or replacement of that hierarchy
cannot remove or cover the action within the app's normal window.

The window refuses key status through canBecomeKeyWindow and is revealed only
with setHidden:NO. It never calls makeKeyWindow/makeKeyAndVisible. Its level is
1001 (above ordinary app content, below native alert windows). Its hitTest
returns only the button's own hit-test result, with coordinates converted from
the window; empty space returns nil rather than the full-screen root view.
The root is transparent and not an accessibility modal. The control remains
88 × 44 points and repositions from its own root view's bounds/safe area on
native layout callbacks. It does not alter the app's safe area or transcript.

Stop, Unsupported/Dormant transitions and application background destroy the
button and overlay. Background/disconnection notifications from the originating
scene also stop/remove it; unrelated scene notifications do not. There is no
global window search, reparenting into keyboard/PiP windows, polling timer or
React tree change. Capture still enqueues its request before changing button
state, and the UI still defers updates until the first frozen-history transfer.

A host regression executes the production show/hide/hit-test/layout/capture/
scene-lifecycle functions against a UIKit facade. It models settings removal
and app root replacement, tests button-only touch routing and non-key policy,
repositions after safe-area/rotation changes, checks the first-transfer boundary,
and exercises Stop/readiness/background/scene teardown. The typed UIKit
geometry boundary is supplied by the facade; actual scene compositing, touch
delivery, VoiceOver, keyboard focus/draft/selection and rotation require device
validation. Host success does not establish those device properties.

Apple's documented window contracts used here:
[canBecomeKeyWindow](https://developer.apple.com/documentation/uikit/uiwindow/canbecomekey?language=objc)
and [visibility without making key](https://developer.apple.com/documentation/uikit/uiwindow/makekeyandvisible()?language=objc).
Earlier candidate artifacts and their original validation records remain intact.

Build-22 local validation: 212 tests ran, 210 passed and the two Apple-only
Foundation/ImageIO checks skipped. Exact compiled Hermes validation passed both
predecessors. Native artifact, receipt freshness and documentation checks passed.
The settings-to-chat overlay transition still requires the next device run.

Build-22 candidate source: `e893730d4b9e15f403ab7e58f8b60a02e61dc230`.
The unsigned IPA passed package verification. The packaged framework exactly
matches the verified native build; original donor HBC and all three native
UUID/text identities remain unchanged.

- IPA SHA-256: `170b3ed918ae4e434588e4ad7462f74f22fb1f49a55a328678fe136022a3a34b`.
- Framework SHA-256: `47d062c216df5ad0bc82a7a43a100ad770a658b80fac4e3a13b1b0a3cc2cbc5d`.

The workspace artifacts directory contains the build-22 IPA, checksum,
`build22-validation.json` and `BUILD22_TESTING.md`. Device confirmation is pending.


### Build-22 device baseline: normal chat, no missing messages

The device user confirms that the in-chat button displays Capturing briefly
and returns to Capture. Copy Capture produced a numeric-chat-v1 report for
Twitch 31.6.2 (262872150334984303), ABI1, generation 3 / sequence 2, with
392 rows, 10,467 wire bytes, complete=1 and interrupted=0. The user explicitly
states no missing messages occurred in this capture. Treat it as a normal-chat
baseline, not a gap reproduction. This confirms the device capture/report path
and reported return to Armed, without establishing untested keyboard, VoiceOver,
rotation or performance properties.

Selected original numeric observations:

```text
Manifest SHA256: 96836cc5491c68d475c436caff9a4862db402f74cb3d35342c8dc88c184fbb28
0,38386,0,0,0,0,267,0,0
3,38388,4,1,0,0,391,0,91
4,38388,8,1,0,0,150,140,149
7,38388,8,1,0,0,5439,382,5821
6,38390,8,1,0,32,1823,64,64
5,38390,0,0,0,375,0,6012,167
```

The frozen history begins around 38.386 seconds after Arm. Header a=267 counts
ordinary observations skipped by diagnostic admission limits, not lost chat
messages; priority admission skips and alias evictions are both zero. Coverage
mask 375 records installed translation, emission, local-echo, store, IRC-reward,
reward-store-route and list families. The coverage row records zero adapter
errors. A reward-store-route event is present, without independent PubSub
provenance. Complete=1 confirms completed report transport; it does not imply
exhaustive event or membership collection.

The snapshot reads 391 store entries and 150 list entries, with 64 membership
samples from each side and membership-truncated flag 32. Different store/list
counts alone do not establish loss. No store-unavailable, list-unavailable,
work-budget, changed-revision or transfer-truncated flag is present in this
snapshot status. The recorded snapshot duration is 1,823 microseconds; this is
an adapter timing observation, not a device-wide performance measurement.

Sampling limitation identified from this baseline: list start/end are 140/149,
but sampled list membership covers indices 22–85; store samples cover 263–326.
The current loops begin at length minus the total membership allowance and
then stop after their shared budget is consumed, omitting the actual visible
range in this case. This is a diagnostic sampling limitation, not evidence of
a chat defect. Before using a snapshot to compare visible-message membership,
prioritize the admitted visible range and explicitly label any tail fallback as
specified by the proposal. This baseline cannot establish absence of any
unsampled visible message, filtering/deduplication or server acknowledgment.


### Further build-22 device feedback and gap capture supplied 2026-10-24

The user separately confirms that the capture action remains visible in
landscape. This establishes reported landscape visibility, not exhaustive
rotation, focus, accessibility or hit-testing validation.

A subsequent build-22 report was supplied as a chat-gap capture. Asked whether
the symptom was blank space, known missing messages or both/uncertain, the user
selected both/uncertain. Preserve that ambiguity; no particular missing message
or affected row is identified. The report uses the same manifest hash and donor
as the normal-chat baseline. Generation 3 / sequence 2 do not uniquely identify
a capture across launches and must not be used to merge the two recordings.

Selected original observations from the new report:

```text
Capture generation=3 sequence=2 rows=163 wire_bytes=4286 complete=1 interrupted=0
0,9598,0,0,0,0,0,0,0
3,9598,4,7,0,0,127,0,10
4,9598,8,7,0,0,127,119,126
7,9598,8,7,0,0,4703,303,5006
9,9600,8,7,39,1,29,-1,1117
9,9600,8,7,40,1,30,-1,1155
9,9600,8,7,41,1,31,-1,1193
6,9600,8,7,0,32,1668,64,64
5,9600,0,0,0,375,0,2556,73
```

The report completed without interruption. Header admission skips (ordinary
and priority) and alias evictions are zero. Its ordinary ring has only 28
events, below capacity 256. Nine labels (1–9) each have paired translation and
emission observations with no recorded callback exception. Store notifications
continue during the approximately 9.6-second armed interval. This supports
continued execution of these observed paths; it does not prove receipt of every
server message or successful rendering. Coverage mask 375 and zero adapter
errors match the installed probes. The snapshot records 1,668 microseconds and
membership-truncated flag 32, without unavailable/read-budget/change/transport
truncation flags. Store paused is false.

Both the store and transcript data contain 127 entries at capture. Their
sampled indices 0–63 have matching labels 10–73 at corresponding indices.
Equal counts and matching partial samples cannot establish equality of all
127 entries, delivery of each tracked message, or correct pixel rendering.
The nine live-event labels are outside this sampled membership and therefore
cannot be followed into current store/list membership from this report.

The donor list reports range 119–126, scroll 4703, viewport length 303 and
content length 5006 (the reported viewport reaches the content end). The
recorder instead samples indices 0–63 on both sides. This repeats the already
recorded sampling defect: starting at max(0,length-128) and spending half of
the shared allowance on each side can omit the entire current list range and
the newest messages. Actual native/pixel geometry is not observed, so the
range is donor state rather than independent visibility evidence.

Known sizes are unavailable for sampled list indices 29–31; their size field
is -1 and their per-row flag is 1. These are older entries outside the reported
current range. Their presence is not evidence that those rows caused the gap,
and this report does not establish whether the symptom is missing data or
blank rendering/layout space. The next diagnostic correction should prioritize
the admitted current list range and relevant bounded associations before
older history, while retaining existing work/privacy limits and accurately
reporting incomplete coverage. No chat-loss or layout root cause is established
by this capture.


## Build 23: viewport-relative immutable snapshots

Build-22 baseline and gap reports sampled older list entries while omitting
the reported current range. Build 23 changes the existing capture projection;
it adds no app hooks, lifecycle probes, per-message bridge calls, polling,
renderer/Fabric instrumentation, or native measurement operation.

Capture still freezes and transfers its existing event history before any
current-state read or reporting UI update. It next reads the existing admitted
LegendList getState result. Exact-donor replay now explicitly verifies that
result.start/end expose startNoBuffer/endNoBuffer rather than the buffered
range. It samples all available visible indices first, across both admitted
scopes, then at most two adjacent indices per side, nearest first. Store state
and its bounded tail are read only after visible rows and margins. A missing or
invalid range is reported unavailable; any bounded tail fallback is labelled
and never described as a visible-range sample.

All entry projections continue to share max_entries=128 and the smaller
callback/JS-work deadline (2 ms in the shipped manifest). More than 128 visible
rows, exhausted time, failed row reads, missing margin or changed scope/store
revision produce explicit partial coverage. Entry exhaustion is distinct from
time exhaustion. An empty valid range is explicit. A successful range sample
does not imply that every sampled row has an available identity or measured
height; those fields have their own status. No list scrolling, mounting, layout
forcing or getter retries are added.

Each list-member row records its list index, existing per-arm anonymous label
where available, measured-height cache status/value, cached position and
counterpart-store membership status. All list observations precede store-tail
projections. Associations use only the already admitted object/id/nonce fields
for bounded transient equality; source objects are not copied or exported.
Matching store projections reuse the sampled list label even if the bounded
global alias map evicts an older association during the snapshot. Object-only
identity and unavailable identity are explicit.

Counterpart membership is present when directly matched, absent only following
a complete stable scan with comparable identity fields, and unknown otherwise.
Incomplete store/list sampling never establishes absence. A changed revision,
mount or array length downgrades the affected snapshot's membership claims to
unknown and its range to partial. The existing independent work and privacy
limits remain in force. This does not add confirmed nonce reconciliation or
server acknowledgments.

Measurement comes solely from getState().sizes (the original sizesKnown Map)
using has/get. Missing entry, exact measured zero, invalid measured value and
unavailable measurement access are distinct. Cache absence means no current
known measurement; these adapters cannot establish whether the row was ever
measured before a cache clear/eviction. A cached measured zero survives the
actual donor getter unchanged. Height is exported in 1/1000 logical points;
exact-zero status is tested before rounding. Finite bounded negative heights
are retained and marked invalid, rather than conflated with unmeasured values.
Cached positions remain rounded logical points. Neither elementAtIndex nor
sizeAtIndex is invoked, and their idCache mutation remains forbidden. The
existing exact getter graph is replayed behind mutation traps; the projection
fixtures also trap writes to source state, data, lines and idCache and check
measurement-map size preservation.

### Report and registry versioning

Manifest revision 3 selects rn-chat-current-v2 and numeric-chat-v2. Revision 2
and prior device artifacts remain unchanged. The numeric transport version is
2, with the same nine-integer row envelope and original kinds 0–9 plus kind 10
for range coverage. Native scalar parsing accepts bounded signed payload
integers (±10,000,000); structural fields retain their existing nonnegative
checks. This preserves negative scroll/position geometry such as overscroll
instead of rejecting a complete capture. Native rows, packet bytes, batches,
deadline, generation/sequence and privacy bounds remain unchanged. The report
identifies units and every status flag; old packets are not silently interpreted
with the new height units.

List member a/b/c are index, measured height in milli-points and rounded-point
position. Member flags are 8 counterpart present, 16 absent after a full
comparable scan, 32 unknown, 64 identity unavailable, 512 object-only identity.
List flags additionally identify 1 unmeasured in current cache, 2 exact measured
zero, 4 invalid measurement, 1024 measurement unavailable, 128 visible and
256 margin. For kind 10, a/b/c are requested first/last and visible rows sampled;
flags are 1 complete including margin, 2 partial, 4 unavailable, 8 partial
margin, 16 tail fallback, 32 empty list, 64 changed and 128 budget reached.
Report completion continues to describe transport separately from these range
and membership coverage results.

### Interpretation boundaries

Where complete comparable membership establishes store-present/list-absent,
investigate store-to-list reconciliation. A list row with cached zero, negative
or suspicious height is a lead for list layout/virtualization, with the cached
measurement's age/native-geometry limits retained. Normal cached row geometry
cannot prove a Fabric text component displayed content; blank presentation
would require further evidence. Missing lifecycle observations may reflect
upstream delivery or missing observation coverage and do not alone prove a
message was dropped. No automatic root-cause classification is added.

Tests reproduce both device ranges (119–126 of 127; 140–149 of 150), a middle
viewport, two scopes, margins, oversized ranges, time and entry exhaustion,
failed/unavailable getters, invalid/empty ranges and labelled fallback. They
exercise positive fractional heights, exact zero, absent/invalid/unavailable
cache entries, object-only identity, complete/partial membership scans, changed
snapshots and forced alias eviction. The actual owned graft and modified donor
factory run in pinned Hermes for both original and complete functional
predecessors. A native report test round-trips the new statuses, signed
geometry and height units, and refuses old-version or out-of-range rows.
Actual device confirmation of the corrected viewport capture remains pending.

Build-23 local validation: 214 tests ran, 212 passed and the two Apple-only
Foundation/ImageIO checks skipped. Both exact compiled Hermes predecessors
passed viewport, identity, measurement-state, budget and mutation-trap cases.
Native report/manifest fuzzers each passed 20,000 malformed-input cases under
AddressSanitizer/UndefinedBehaviorSanitizer. Native framework verification,
validation-receipt freshness and documentation checks passed. Device validation
of the corrected viewport range remains pending.

Build-23 candidate source: `b8a62d458097e5a78af9a5582dc438853ed7b6da`.
The unsigned IPA passed package verification. Its framework matches the verified
native build; original donor HBC and all three native UUID/text identities remain
unchanged. Prior manifests and device-test artifacts remain intact.

- IPA SHA-256: `118f60af34b9d3a3d2125afecf85a958aad8c38f97cd0ebb75e39a8ef82ee673`.
- Framework SHA-256: `1b06e86acb974a6fcca7e75cdd11f7667a9446e5f76357be0d9201e2e021d60c`.

The workspace artifacts directory contains the build-23 IPA, checksum,
`build23-validation.json` and `BUILD23_TESTING.md`. The report now identifies
numeric-chat-v2 and manifest hash `60f94c27ec7c4df13dd62fe2aa35586badc871c72cb29540b9aa13ef7b047177`.
Device viewport validation is pending.


### Build-23 device gap report: viewport confirmed, store membership incomplete

The user reports another chat gap and supplies a build-23 numeric-chat-v2
capture with the expected manifest hash. Generation 11 / sequence 10 contains
56 rows and 1,567 wire bytes, complete=1 and interrupted=0. Header ordinary/
priority admission skips and alias evictions are zero; coverage mask is 375
with zero adapter errors. The user hopes this captured the symptom. The report
establishes the sampled state, not independently that a blank/missing message
was still visible at the exact snapshot instant.

Selected original observations:

```text
0,10750,0,0,0,0,0,0,0
1,8960,0,12,9,0,2,0,0
1,8961,1,12,9,0,2,0,0
1,9582,0,12,10,0,2,0,0
1,9582,1,12,10,0,2,0,0
4,10751,8,12,0,0,150,142,149
7,10751,8,12,0,0,5605,303,5908
9,10752,8,12,1,160,142,34000,5596
9,10752,8,12,2,160,143,40000,5630
9,10752,8,12,3,160,144,34000,5670
9,10752,8,12,4,160,145,40000,5704
9,10752,8,12,5,160,146,34000,5744
9,10752,8,12,6,160,147,34000,5778
9,10752,8,12,7,160,148,40000,5812
9,10752,8,12,8,160,149,40000,5852
9,10752,8,12,11,288,141,40000,5556
9,10752,8,12,12,288,140,34000,5522
3,10752,4,12,0,0,151,0,11
10,10753,8,12,0,129,142,149,8
6,10753,8,12,0,36,2040,7,10
5,10753,0,0,0,375,0,684,19
```

Viewport priority is now confirmed on the reported device: all eight indices
142–149 were sampled before the two available margin indices, 141 and 140.
Range flag 129 is complete-including-margin (1) plus budget-reached (128); the
work limit was reached during later membership work, not before the visible
range was captured. Snapshot flag 36 is work-budget (4) plus membership partial
(32), and the recorded total projection duration is 2,040 microseconds.

All ten list rows have available positive cached heights of 34 or 40 logical
points. There are no unmeasured, exact-zero, invalid or unavailable-height flags
on these rows. After sorting by index, every next position equals the prior
position plus its measured height: 5522/5556/5596/5630/5670/5704/5744/5778/5812/
5852. Thus no inter-row gap appears in this cached numeric geometry. The last
row ends at 5892 while reported content length is 5908; that 16-point trailing
extent alone does not establish a fault, since native pixel geometry and
footer/inset attribution are not captured here. The reported viewport ends at
5605+303=5908. Normal cached geometry cannot rule out native/Fabric blanking or
prove that the text content was displayed.

Ten labels have translation/emission pairs in the frozen history. The visible
tail contains labels 1–8; the later labels 9 and 10 reached those two lifecycle
callbacks but are not among the sampled tail rows. With zero alias evictions,
this is a useful bounded progression lead, not proof they are absent from the
entire list, absent from the store, or dropped. Filtering/deduplication,
reconciliation and actual presentation remain unobserved. Store/list counts
151/150 do not prove a mismatch: differing counts also occurred in the known
normal baseline and may reflect bounded list data or other normal processing.

All list-member flags are 160 (visible + membership unknown) or 288 (margin +
membership unknown). The store scan sampled only indices 33–39, with labels
13–19 and unknown counterpart membership. It exhausted its remaining 2 ms
work allowance before reaching recent store entries or the relevant identities.
The existing loop starts at the oldest edge of its bounded tail allowance and
walks forward. Device evidence now shows that an early deadline can spend all
remaining work on those older entries. A subsequent optimization within the
same adapters/budgets should examine newest/relevant store entries first;
partial scans must retain unknown, never absent, membership. No new native or
Fabric instrumentation is justified by a root-cause claim from this report.

This capture confirms the requested visible-range projection and supplies
normal cached geometry during a reported gap. It does not yet distinguish
store-to-list progression/filtering from native/Fabric presentation, or establish
an upstream delivery failure. No functional chat fix or new candidate was made
as part of interpreting this device report.


## Build 24: newest-first store traversal under the unchanged deadline

The build-23 device gap capture completed its viewport but spent the remaining
work allowance on store indices 33–39. Build 24 reverses traversal of the same
bounded tail: begin at store length minus one and move backward, retaining
the original viewport-first, margin-second ordering and comparing existing
viewport targets before margin targets. It does not guess a store index from
a list index or assume equal store/list lengths. Newest entries are examined
first, which prioritizes the likely counterparts for the end-of-chat viewport
and recent observed messages.

Every manifest limit is identical to revision 3: the callback deadline remains
2,000 microseconds, JS work allowance 10,000 microseconds, shared entry allowance
128 and all transport/privacy/rate limits unchanged. The effective snapshot
deadline remains the smaller of the callback and JS-work limits. Each next
entry and each identity comparison still checks that deadline; no work is
deferred to another snapshot task or resumed after expiration. An individual
already-entered read/comparison is not preemptible, as in earlier candidates.
No new app hooks, live event stages, getters, timers, layout operations or
per-message bookkeeping are added. History still freezes/transfers first;
elementAtIndex and sizeAtIndex remain forbidden.

A new kind-11 numeric row records store slots successfully read, lowest read
index and highest read index. Failed accesses do not count as successful reads
or establish that the newest slot was reached. If a slot is read but later
identity projection/comparison fails, the read still counts while the failure
and incomplete-comparison flags identify the limitation. Extrema do not assert
that every intermediate slot was successfully projected. A separate flag marks
all captured store slots read; that is not equivalent to complete, stable
membership correlation.

Traversal flags are 1 store available, 2 newest entry read, 4 all store slots
read, 8 time budget, 16 entry limit, 32 read failure, 64 changed snapshot,
128 empty store, 256 alias continuity limited and 512 comparisons incomplete.
Unavailable/empty stores and a deadline reached before the first read explicitly
have zero examined entries and no newest-entry-read flag. Entry exhaustion is
not misreported as time exhaustion. Unmatched/unread membership remains unknown;
absence still requires the existing complete, comparable and stable scan.

The copied/exported report adds human-readable per-scope traversal summaries,
including examined/total counts, read-index extrema, whether the newest entry
was read, stop limits and failures. It also summarizes existing visible-row
store membership and up to eight recent distinct retained lifecycle labels,
with store/visible-list observation counts. Recent labels are selected by
recorded elapsed time from the frozen translation/emission/local-echo rows,
deduplicated and scope filtered. These are observations in the bounded saved
capture, not all server messages or proof of global absence.

Recent-label matching is performed only by tas_inv_report_format on explicit
Copy/Export, using numeric frozen rows. The production call-site audit finds
the formatter only in the explicit report-export UI. It does not run in
tas_inv_report_accept, the JS projection, or any per-message callback. This
keeps that extra correlation work outside the capture's 2 ms allowance and
requires no additional raw identifiers or retained live objects. Changed
snapshot/alias flags remain visible; observation counts are not promoted into
stable membership claims.

Manifest revision 4 and numeric-chat-v3 / rn-chat-current-v3 identify the new
traversal row and summaries. Earlier manifests and artifacts are unchanged.
The same nine-integer envelope, signed scalar limits, immutable native parser,
generation/sequence checks and runtime ABI1 remain. The numeric transport
version is 3 and old packets are not silently interpreted as the new profile.

Regression cases reproduce a seven-entry time limit: indices 150,149,148,147,
146,145,144 are read instead of 33–39, while the complete viewport remains
sampled first. Tests cover expiration before traversal, a failed newest read,
entry exhaustion, complete/empty/unavailable stores, changed snapshots, alias
continuity limits and conservative membership. The native formatter tests
scope filtering, recent-label deduplication/selection, viewport counts and
explicit unknown results. The sanitizer seed includes more than eight retained
lifecycle labels and traversal rows so bounded export-summary selection executes
under the malformed-input harness. Device confirmation remains pending.

Build-24 host validation: 216 tests ran, 214 passed, and the Apple Foundation
and ImageIO checks were skipped on this Linux host. Pinned compiled Hermes
replay passed on both donor predecessors; report and manifest sanitizer harnesses
each passed 20,000 malformed-input cases under ASan/UBSan. Native artifact
verification, documentation checks and whitespace checks passed. All manifest
limits were compared against revision 3 and remain identical.

Build-24 device candidate provenance:

- Source commit: 365214477eab053134c852ee0d3c9ea80eace6d6.
- IPA: Streamside-3.1.0-build.24-modular-diagnostics.ipa.
- IPA SHA-256: 1d7179fc899c32c297803623a2e1808838e3262c56bded4021e00ec14e87d530.
- Framework SHA-256: 76e773b9d7224390b431f28947558634886493055f66abe18950988e0f9a0e2f.
- Manifest revision 4 SHA-256: 44e05c219d39bd41a690f9151f4633b9d16b2a9aa959beaada9317ab76f50b88.

Unsigned IPA verification passed against the guarded framework. Independent
checks confirmed the packaged framework/version, original HBC digest and all
three donor native UUID/text identities. External build24-validation.json and
BUILD24_TESTING.md preserve the complete validation and device handoff.
Earlier artifacts/hashes remain unchanged; device acceptance remains pending.
