# Native frontend VAFT integration trial

2026-11-17, `feat/native-frontend`, following `b62e975` (device confirmation of
preview dismissal and cold-audio fixes). This ports the existing pinned native
VAFT solution 24 strategy into the SwiftUI playback path. It does not change the
upstream pin or claim device ad suppression before an actual ad-bearing test.

## Implementation and ownership

Settings → Player → Playback has an **Ad blocking** toggle, enabled by default.
It persists under `dev.streamside.player.adblock` and applies to the next opened
stream or preview. Watch promotion retains the current preview's player and
filtering lease. Off uses the original iOS/site token parameters and unfiltered
Foundation loading for subsequent playback.

The playlist engine is extracted from `src/Streamside.c` into
[`TASVAFT.h`](../../src/TASVAFT.h), used by both the legacy and native frontends.
The alternate order embed → popout → autoplay, exact generation-bearing stream
ownership, rendition matching, clean-variant reuse, stitched/MIDROLL markers,
relative URL rewriting and remembered ad-segment fallback are retained. The
pinned blank-media payload is shared in `TASVAFTBlank.h`. Its legacy allocator now
uses NSData's actual base64 initializer, replacing the unsupported class-selector
form; the Apple transport fixture checks actual payload bytes rather than a stub.
Attribution and upstream identity remain in [Upstream](../UPSTREAM.md).

[`SSNAdBlock.m`](../../native/SSNAdBlock.m) is the separate native adapter. It
links the shared engine, not the legacy constructor, emotes, asset-loader,
credential/header capture, RN patches, or legacy diagnostics UI. After the native
launch choice and runtime-probe registration, it registers a Foundation URL
protocol and adds it to session configurations before IVS is created. Apple's
[protocolClasses documentation](https://developer.apple.com/documentation/foundation/urlsessionconfiguration/protocolclasses)
explains the per-session mechanism and excludes background sessions; the adapter
leaves those configurations alone. Original Twitch launch mode installs none of
these hooks and remains an unfiltered startup control.

Admission requires an active native playback lease, GET, HTTPS, a proper Twitch
or ttvnw host boundary, and either an HLS path or an exact remembered ad segment.
The adapter does not admit account/API calls or arbitrary image/content URLs.
Its internal session predates registration and guarded inner requests cannot
recursively intercept themselves. Rewritten responses replace origin length and
encoding metadata; original errors/status and unrecognized bodies retain their
native outcome. There is no second player or media request through JavaScript.

The initial native token query changes only site → popout, keeping the iOS
platform, as the legacy request normalizer did. Alternate requests use the
existing inspected `PlaybackAccessTokenParams` / `StreamAccessTokenQuery` ABI,
with embed/popout + web and autoplay + android. There are no new private ABI
entries, Swift layouts or witness-table assumptions. All 55 existing admissions
remain mandatory. Authorization, client-integrity and refresh continue through
TKGraphQL/TWApolloClient. The adapter never reads OAuth/header strings, generates
a device identity or substitutes the legacy public persisted-query transport.
Media token dictionaries remain private to request processing and never enter
SwiftUI, preferences, reports or logs.

A single serial worker owns playlist processing and bounded alternate waits.
There are at most 32 admitted queued requests, a 15-second total work deadline
and at most six seconds per token/network wait. Native promises are created and
polled on main without blocking it. Close, background, account invalidation and
new playback invalidate the lease; stopped requests and stale work cannot deliver
or create later alternate requests. Original promise cancellation and native
account identity checks remain in effect. Old lease endings cannot cancel a newer
lease. The engine is cleared on a new playback generation. Mute-before-load,
audio setup/retirement queues, single-player Watch handoff and theatre controls
are unchanged.

## Diagnostics

Native reports add `adblock_enabled`, `adblock_installed` and `adblock_metrics`.
These are booleans and eleven numeric counters, independent of runtime probes:

| Index | Observation |
| --- | --- |
| 0 | HLS requests intercepted |
| 1 | Master manifests |
| 2 | Media manifests |
| 3 | Ad-marked manifests |
| 4 | Clean alternate selections |
| 5 | Ad segments remembered for suppression |
| 6 | Alternate native-token failures/timeouts |
| 7 | Unmapped media manifests |
| 8 | Synthetic blank-segment responses |
| 9 | Legacy GraphQL rewrites; native path does not use this hook |
| 10 | HLS transport failures/HTTP errors |

Normal cancellation is excluded from failure counters. Increments are bounded
per call; unknown indices are ignored. Diagnostics show the toggle/transport state
and interception/selection counts. Zero intercepted requests means unobserved
transport coverage, not successful filtering. Clean playback without a detected
ad opportunity is not suppression evidence. Runtime probe calibration requirements
are unchanged. No legacy log text, manifests, media grants, URLs, headers or
channel/account identifiers are added to exports.

## Validation and remaining device work

Host tests execute the shared production engine with synthetic network/Foundation
values: markers, ordered alternates, clean reuse, independent streams, stale
references, unmapped variants, segment fallback and closest-rendition matching.
The existing URL-protocol tests and full gated Linux/Zig legacy build pass.
The native host suite also tests bounded diagnostics, original-mode isolation and
component rejection when new receipts are missing. Exact test/build records are
in [host validation](SWIFTUI_NATIVE_VAFT_HOST_VALIDATION.json).

Apple CI adds a mandatory real-Foundation fixture using the production adapter
with a fake network/native promise. It covers default On, Off passthrough, Off
restoration in a fresh process, untouched baseline mode, native token parameters,
clean alternates/cache, stream isolation, actual blank-media bytes, cancellation
and account loss. A strengthened UIKit facade receipt checks every filter lease
ends once across lifecycle cancellation. All previous playback/audio, decoded
video clipping, source preview/gesture, animation pixel, auth/navigation,
networking and component gates remain required. Missing new receipts reject
components. These Apple results are pending submission/completion; they cannot
be established from Linux host tests.

After successful Apple compilation and local donor packaging, install with the
same Feather application/keychain identity. Compare On and Off by leaving and
reopening the same stream/preview, including an actual preroll or midroll
opportunity. Export Native diagnostics after each case. Check real video/audio,
preview silence and uninterrupted other media (including first preview), Watch
handoff, rapid closing, background/reopen and account changes. Confirm HLS
interception and actual ad-marked/alternate or segment evidence before claiming
ad suppression; preserve failures. Review RN/Hermes counts with the existing
coverage/calibration limits. The exact Twitch 32.0 donor remains local and must
pass normal identity/ABI/package checks before modification. No donor or signing
material is part of Apple inputs or artifacts.

## First Apple build failure and correction

Source `39316301b2b71929520379bbf7d871b669189e94` failed in
[Codemagic](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afd2915d133a39c4a12816b).
The [failure record](SWIFTUI_NATIVE_VAFT_BUILD_FAILURE_1.json) preserves the
archive hash, successful stages and validation limits. SwiftUI and the ARC native
VAFT adapter compiled, but the C token-request translation unit rejected an
unconditional Objective-C retained-result annotation. Warnings remain errors.
Linking, the real-Foundation transport fixture and simulator gates were not reached.

The annotation is now limited to Objective-C consumers, keeping ARC's retained
result contract and the existing manual C ownership. A new host regression compiles
the actual header and caller as both C and ARC Objective-C for arm64 iOS. All 86
native host tests pass (9.622s). Filtering, auth, service ABI and mandatory Apple
gates are unchanged. Only trailing whitespace was removed from the extracted
engine header. The first host record and failed source retain their original
identities; replacement Apple success and physical ad suppression remain pending.

## Successful replacement Apple build and package

Source `a3d98aaab409c137de6e5dd651bae6c638da1fb8` passed
[Codemagic](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afd38d2d133a39c4a12855b).
The [successful validation record](SWIFTUI_NATIVE_VAFT_VALIDATION.json) retains
source/proof/toolchain identities, test receipts, stage timings and package hashes.
All real-Foundation VAFT fixture assertions passed, including fresh-process Off
restoration and untouched original mode. UIKit confirms the playback filter lease
lifetime, all prior cold-audio/retirement checks, source preview/gesture behavior,
actual decoded-video clipping and both player-control styles. The 63 required
post-download ABI, component, diagnostics, launch, probe, comparison and shared
engine tests passed. Earlier pending statements describe their original scope;
this is their successful Apple follow-up. The first failed build remains preserved.

Ubuntu verified the exact donor before assembling the test IPA, including all
retained donor entries and unchanged original HBC. The IPA is local under
`artifacts/native-frontend/native-vaft-a3d98aa/` and requires Feather signing
with the existing application/keychain identity. No new independent baseline IPA,
VM dependency, signing upload or proprietary CI input/artifact was introduced.
Real Twitch ad-bearing playback and device regression checks remain pending.

For device review: install, open a stream with Ad blocking left On, and export
Native diagnostics after watching. Then switch Off in Settings → Player, fully
close/reopen the app (also checking the saved preference), watch again and export
a separate report. Use a real ad opportunity where available; unobserved ads or
unintercepted requests cannot establish suppression. Include a first-preview
external-audio check and Watch/close regression check.
