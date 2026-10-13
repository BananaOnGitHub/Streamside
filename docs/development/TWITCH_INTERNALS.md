# Twitch internals and donor admission

Streamside integrates with private Twitch structures only after checking the boundary actually used by that donor. A matching class name or app version is not enough.

## Begin with the active surface

Determine the actual theatre/chat path on device before choosing an adapter. The inspected 31.5 donor has both RN and legacy UIKit. Idle legacy hooks in a horizontal-only stream did not mean the old class disappeared from the binary; they meant that surface was using another path.

Trace ingress, message representation, composer ownership, image requests, and presentation separately. Incoming success does not establish own-message display. The native RN input is also separate from Fabric transcript paragraphs.

## Objective-C admission

Check the concrete class and full method encoding, including return type, argument widths, and block signatures. Add an override on the concrete class when an inherited method must be intercepted without changing its superclass globally.

Field reads require named ivars, offset ordering, adjacent-field span, alignment, and instance bounds. Primitive/reference spans do not grant permission to decode unrelated Swift structs. Recheck live class/ownership where needed.

Examples:

- RN IRC socket URL and receive delegate ABI.
- `RCTSource.data` getter ABI and source-owned patched data.
- Legacy per-message subscriber/follower definition getters and `TKChatEmote` constructor identity.
- Exact native input/editor classes, attachment URL bridge, and deallocation hooks.

Runtime retry can install classes loaded later. Missing prerequisites remain missing in diagnostics rather than being patched with approximate offsets.

## Swift values and authority

The legacy catalog bridge checks value-witness sizes for Array, String, and URL before bridging actual native values. It uses dynamically resolved existing runtime functions rather than inventing storage.

A Swift weak class existential is not an ObjC weak reference. The input delegate's offset/span and its runtime load/release path must agree. The current catalog manager and account/room fields remain the authority; an old cached ID is not sufficient after logout/rebinding.

Private Swift workers can bypass ObjC wrappers. Historical catalog publication and footer rebuilds showed this explicitly. Observe the native result/surface or an admitted lifecycle boundary rather than assuming a wrapper intercepts every call.

Do not use historical unslid addresses as live hooks. Archive addresses are donor-specific analysis evidence.

## Hermes source and patch chain

Released 3.0.0 baseline: original 31.5 body, 27,786,480 bytes, Hermes 98,
SHA-256 `422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b`.
Current 3.1.0 development headers target the original 31.6 body: 28,682,408
bytes, Hermes 98, SHA-256
`20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458`.
The [build-5 port record](../investigations/TWITCH_31_6_COMPATIBILITY.md#build-5-hermes-port)
preserves the previous refusal and defines host validation and pending device scope.

[TASRNWidthPatch.h](../../src/TASRNWidthPatch.h) admits the exact target body and appends width-adjusted EmotePart code. Subsequent [local](../../src/TASRNLocalEchoPatch.h), [composer](../../src/TASRNComposerPatch.h), [popup](../../src/TASRNPopupPatch.h), and [strip](../../src/TASRNStripPatch.h) stages validate their expected predecessor/function metadata.

`RCTSource` owns a cached patched NSData. The donor file and original caller data remain unchanged. Each stage recomputes the footer and preserves unrelated function/data/debug structures according to its verified layout.

Hermes function IDs, Metro module IDs, and React component identities are different domains. In the 31.5 investigation, factory 4884 registered Metro module 4880; importing 4884 as the module caused a real missing-menu failure while an equally incorrect mock passed. The 31.6 binding is factory 4941 / module 4937 and is verified against that donor's registration.

## Register and exception correctness

Do not infer executable correctness from a valid disassembly alone. Hermes outgoing calls stage argument registers sequentially before loading the callee. Build 59's frame-18 injection clobbered its own callee before native entry; frame 21 corrected the overlap.

Exception coverage must include only added preview work and resume original emission. Catching Twitch's original send/translation errors would alter application semantics.

The inspected Hermes-98 large header is 40 bytes with flags at byte 36. An older development parser schema used 36/35. Analysis must agree with the compiler/runtime, not merely with the parser's initial schema.

## React grafting

Owned installers replace verified writable leaf exports and restore originals on failure. Public barrels can expose live getters and are not necessarily writable.

Preserve donor hook ordering. The native autocomplete adapter adds no new React hooks to an already-rendered donor call sequence. Provider/native card components use separate trees. Input/library/settings contexts scope state; global last-room/draft state is not a safe substitute.

Demand-only wrappers retain original image type/source/style/handlers. They observe committed instances and bounded scalar metadata, not speculative render attempts or physical native identity.

## Tools and checks

- [verify_rn_width.py](../../tools/verify_rn_width.py): original/changed bytecode, branch/header/call-frame checks.
- [verify_rn_popup.py](../../tools/verify_rn_popup.py): provider card graft and donor binding.
- [rn_graft.py](../../tools/rn_graft.py): payload generation/relocation and required validation constants.
- [build_snapshot_runtime.py](../../tools/build_snapshot_runtime.py): pinned runtime/runner evidence.
- [validate_rn_snapshot.py](../../tools/validate_rn_snapshot.py): production payload execution, native acceptance, real donor window/settings checks.

The runner source revision is `40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c`. Required inputs and commands are in [Building](../BUILDING.md).

## Porting checklist

1. Preserve the original donor fingerprint, app/build, framework identities, and analysis inputs.
2. Confirm live architectures and actual callbacks before choosing a seam.
3. Validate native ABI, field spans, value bridges, and account/channel ownership.
4. Re-resolve function headers, module registrations, writable exports, constant/literal kinds, and feature-flag adapters.
5. Verify instruction boundaries, branch targets, register liveness, outgoing-call slots, and exception intervals.
6. Recompile/regenerate owned payloads and run exact-donor plus compiled-runtime gates.
7. Run focused device tests for both renderer paths, native fallback, composition, rendering, lifecycle, and playback.
8. Record unsupported boundaries explicitly; do not relax checksum admission to guess compatibility.

The [archive](../archive/README.md) preserves the representation, paragraph-placeholder, and native-seam discoveries. [Testing](TESTING.md) distinguishes structural, runtime, and device evidence.
