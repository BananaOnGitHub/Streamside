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
