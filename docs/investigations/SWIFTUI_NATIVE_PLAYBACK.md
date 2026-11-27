# Portrait native playback trial

Work began from clean `feat/native-frontend` at `b87d458ad69a2cf0068b5512e5eba86be0d85866`.
The preceding endpoint-feedback fix is device-confirmed by the user; its custom
thumb lost Liquid Glass styling. Earlier records and package identities remain
in [the slider trial](SWIFTUI_CYCLE_SLIDER_FIX.md). This trial adds the first
Streamside theatre; earlier no-runtime results do not establish playback isolation.

## Implementation

[CycleSlider](../../native/swift/CycleSlider.swift) retains its own seven-stop
selection and feedback gating. Its thumb now uses the public iOS 26
`glassEffect(.regular.interactive(), in: Circle())`; earlier iOS and Reduce
Transparency retain the opaque fallback. This changes appearance without restoring
the system stepped slider's automatic feedback. Reduce Motion still disables the
cycle control and preserves its saved choice. Apple's
[interactive glass API](https://developer.apple.com/documentation/swiftui/glass/interactive(_:))
is the visual interaction boundary; physical appearance/feedback require a device.

A live row opens [NativeTheatre](../../native/swift/NativeTheatre.swift) through
the existing guarded [SwiftUIHost](../../native/swift/SwiftUIHost.swift). The actual
presented UIKit hosting controller supports portrait and requests portrait scene
geometry. A 16:9 native player surface sits at the top, status/title below it, with
space reserved for future chat. Close and Diagnostics remain accessible. Restricted
rows are refused with an explanation: this trial does not implement Twitch's
content-consent gates. No chat, mini-player or PiP is constructed.

The dedicated [request adapter](../../native/SSNPlaybackRequest.c) uses the existing
`TKGraphQL.sharedInstance.apolloClient`, the donor's generated
`PlaybackAccessTokenParams` / `StreamAccessTokenQuery`, and native
`TWApolloClient.fetchAsPromise(query:cachePolicy:)`. The existing HTTP authorization,
client-integrity and Apollo response/error machinery remain in the request path.
No account OAuth value/header is read or copied. Requests require the same opaque
native authorization object that supplied the verified account, and no monitoring
failure. The query explicitly uses platform `ios` and interactive player type
`site`, with the nullable arguments matching the inspected native live request.
Its validity for device entitlement is pending an actual request.

This is reuse of the native query/client, **not** a claim to have reused the private
`StandardMediaPlaybackSourceRequester` or its cache. Those newer requesters use
private Swift async/generic boundaries. The facade constructs the Usher HLS URL
with NSURLComponents and the returned short-lived media grant; IVS loads its
manifest/segments and enforces the signed policy. Neither the grant nor URL crosses
into SwiftUI, diagnostics or persistence. Failed/absent native responses stop the
attempt. There is no public-endpoint fallback, credential extraction, independent
account renewal, or invented account-token refresh policy. Authorization failures,
restrictions, regional/network failures and eventual media-grant expiration remain
device validation cases; no policy or consent gate is bypassed as a workaround.

[SSNPlayback](../../native/SSNPlayback.m) owns the bundled `IVSPlayer` and
`IVSPlayerView`, without embedding another SDK. Typed Objective-C messages follow
exact donor method encodings checked at packaging and again before creation.
Every player operation runs on the main thread. A 250 ms owned poll observes native
promise completion, IVS state/error and decoded-frame presence; requests/loading/
stalls have 30-second timeouts. Playing and decoded-frame observations are distinct.
The facade installs a playback/movie audio session, then restores the prior
category/mode/options on release if they still match its own configuration.
No donor error is stringified because errors can contain credential-bearing URLs.

Leaving cancels pending work, pauses the player, detaches the view, releases its
references and restores owned audio configuration. Resigning active does the same;
becoming active requests a fresh media grant. Account loss/authorization-object
change immediately stops playback. This first iteration deliberately does not keep
background audio. The account manager, login coordinator, restoration notifications,
scene delegate and root-ownership guard remain in place.

## Exact donor and ABI evidence

The only admitted input is Twitch **32.0**, build **263110145453907615**, IPA SHA-256
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
[The admission plan](../../native/twitch32.json) additionally pins TwitchGraphQLAPI,
ApolloAPI and AmazonIVSPlayer image identities. The bundled IVS framework identifies
itself as version 1.58.0, bundle version 1. Existing RN/Hermes patch/probe
entries are unchanged: 25 probes across four armed images, with the same native
fail-before-runtime behavior and matching-proof positive-control requirement.

Selected inspected boundaries (unslid addresses, exact input only):

| Boundary | Image/address | Concrete lowering |
| --- | --- | --- |
| Existing live requester | Twitch `0x1025e0810`–`0x1025e0958` | Nullable inputs, `ios`, native token query and native Apollo execution |
| `apolloClient` getter | TwitchKit `0x2cda90` | Graph self X20; retained two-word client X0/X1 |
| Playback params constructor | TwitchGraphQLAPI `0x75644c` | X0–X7 plus seven stack slots; one-word InputDict result |
| Token query constructor | TwitchGraphQLAPI `0x3ef144` | Name X0/X1, params X2, metatype X20; allocated query X0 |
| Simple fetch-as-promise overload | TwitchKit `0x24d7d4` | Query X0, cache tag W1, client X2/X3, query metadata X4, conformance X5, result X8 |
| Native generated token selection | Twitch `0x100c4614c` | Loads Data's direct word into X0 before exported token getter |
| Optional token getter | TwitchGraphQLAPI `0x5b29d4` | Direct Data word X0; optional token word X0 |
| Signature/value getters | TwitchGraphQLAPI `0x161764` / `0x1433a0` | Direct token word X0; native Swift String X0/X1 |
| IVS init/load/play/pause | AmazonIVSPlayer `0x60ce0` / `0x626c4` / `0x62710` / `0x626cc` | Objective-C encodings recorded in the plan |

Storage sizes, optional tag handling, destruction and Promise generic metadata come
from the runtime's metadata/value witnesses. GraphQLQuery conformance comes from
`swift_conformsToProtocol`; no protocol witness slot is guessed. Runtime admission
requires one-word generated values/promises and two-word Swift String. The adapter
uses 51 admitted Swift function entries total and 11 admitted Objective-C service
entries including the existing logout adapter. Packaging rechecks exports, addresses,
prefixes, Objective-C encodings and whole-image identities.

AWS documents the public
[player/view, main-thread use and background pause](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/ios-getting-started.html)
and [state values](https://aws.github.io/amazon-ivs-player-docs/1.32.0/ios/Enums/IVSPlayerState.html).
Documentation establishes API semantics; the bundled donor establishes actual
available methods/encodings. No current upstream player framework is downloaded.

## Diagnostics and validation boundaries

Exports add bounded numeric `playback_phase`, `playback_error`, `playback_last_error` and nine cumulative
`playback_events`, ordered: opened, native request, player created, playing first
observed, decoded frames first observed, adapter player release, failure,
resigned-active teardown, closed. Each new source request can record another playing/
decoding transition. The release event proves an adapter release call, not SDK
object deallocation or a measured absence of leaks. The last nonzero error survives closing/retrying within the process; earlier
launch reports retain their own recorded states. Counters never contain channel
names, titles, URLs, grants, credentials or native error descriptions. The interface
also shows playback phase/error and created/release counts in Diagnostics.

Phases: 0 stopped, 1 requesting, 2 loading, 3 playing, 4 buffering, 5 inactive,
6 ended, 7 failed. Error categories: 1 session/monitor/navigation unavailable,
2 player ABI, 3 request ABI/input unavailable, 4 native entitlement request failure,
5 audio configuration, 6 timeout, 7 IVS error. A playing flag alone does not prove
visible video/audio or zero JavaScript activity.

The Apple workflow compiles and links both modes, executes existing model/ownership/
clock/title tests, and a new synthetic UIKit playback fixture using production
SSNPlayback with owned fake IVS/GraphQL objects. It checks source percent-encoding,
playing observation, pending cancellation, teardown, background/return and account
loss. Both component sets require the successful receipt. These tests do not execute
the donor or stream real video/audio. Local native host tests pass 55/55,
including 17 compiled ARM64 register-boundary tests and rejection of missing playback
validation and preservation of playback failures after closing. Apple build/package results are recorded separately below when available.

## Device check

1. Sign/install the matching **baseline** with Feather using the established app/keychain
   identity. Exercise Twitch until the baseline reports positive RN/Hermes observations,
   then export the baseline report. Replace it with the matching **native** IPA.
2. Open Settings and check the cycle thumb looks glassy. Hold/jitter both slider ends;
   feedback should occur only when selecting another cycle. Check Reduce Motion too.
3. Tap a live unrestricted followed channel. Confirm portrait theatre, moving video,
   sound and no rotation to landscape. Wait at least 30 seconds and export a report
   from the theatre's Diagnostics button while playback is working (or failing).
4. Close the stream. Confirm audio stops and the followed list remains. Open another
   stream; background/return, then close and export again. Close/reopen the app and
   confirm the account/feed still restore. Recheck logout/login when practical.
5. Send the exports and describe video/audio, teardown and rotation results. Reports
   must show matching calibration, armed mask 15, no monitoring failures and zero
   guarded runtime entries across playback. A blocked runtime attempt/failure must be
   retained and investigated; do not silently permit JavaScript to make playback work.

Actual authenticated stream access, playback, audio, portrait behavior, device
teardown/leaks and RN/Hermes isolation remain **unverified until physical-device
results**. Current Apple compilation/package status is not device acceptance.

## Initial Apple validation failure

The first published implementation was `987b6ff`; its Apple run
[43337102864](https://github.com/BananaOnGitHub/Streamside/actions/runs/43337102864)
was superseded/cancelled after explicit theatre actor isolation and fixture C-bool
corrections in `80b621e`. Linux runs for both revisions passed.

[Apple run 43337348795](https://github.com/BananaOnGitHub/Streamside/actions/runs/43337348795)
for `80b621eb1e9a29092e6566ae5dcbfee75dab0199` failed its baseline component's synthetic
playback lifecycle fixture after successful Swift/Objective-C compilation, linking,
signature verification, models, UIKit ownership and clock/title fixtures. The
receipt was `playing_observed=false`, `passed=false`, with background/return,
account stop, cancellation, teardown and source encoding true. No distributable
components or IPA were admitted from that run. The failure logs are retained
outside the source checkout under `artifacts/ci/failure-80b621e…`.

The fixture initially sampled its first playing/decoding state after a fixed 1.1 s.
The correction waits up to 10 s for the actual required playing **and** decoded-frame
observations, fails immediately on player failure, and captures numeric initial
state on failure. It keeps every lifecycle assertion and does not treat missing
observations as success. The delay hypothesis needs the corrected run; the initial
failure is not reclassified as a pass. The production 30 s timeouts are unchanged.
The refinement also stops media synchronously on Close and preserves the last
nonzero playback error after closing/retrying, tested by the host diagnostic core.

A pre-package static audit of `7138847` found four generated query/params metadata
accessors missing from the admission table. The facade would have failed closed
with request-ABI error 3 before making a request. They are now admitted from exact
exports/prefixes, raising the total from 47 to 51. A host test requires literal
native metadata/function dependencies across the integration/account/feed/playback
adapters to be present in the admission plan. This fixes a validation-coverage gap;
the synthetic player fixture replaces the request boundary and cannot establish
actual donor metadata/service availability. No IPA was packaged or delivered from
the incomplete plan.

[Corrected Apple run 43338741179](https://github.com/BananaOnGitHub/Streamside/actions/runs/43338741179)
for `7138847b37edacd17bdd3e82d07568bca26ebf3e` passed both compiled modes, all
synthetic UIKit playback lifecycle observations, model/ownership/clock/title checks,
17 Apple-compiled ABI tests, component admission 10, core 9, Foundation 1 and
comparison 5. This supports the fixture timing correction. Its incomplete donor
metadata plan remains superseded; no IPA was made from its components. The full
corrected metadata source receives another source-matched build before packaging.

## Validated source and diagnostic packages

Final compiled/packaged source: `2bbfb860e46ac066f83fca870db57370084e730c`.
[Artifact receipts](SWIFTUI_NATIVE_PLAYBACK_ARTIFACTS.json) contain exact source,
proof, donor/build, toolchain, test results, framework/modified-image hashes,
independently recomputed IPA hashes and retained workflow/failure-log hashes.

[Apple Actions 43340009333](https://github.com/BananaOnGitHub/Streamside/actions/runs/43340009333)
passed with pinned Xcode 26.6 / 17F113, Swift 6.3.3 and iPhoneOS SDK 26.5. Both
frameworks compiled/linked and passed ad-hoc signature verification. Both model
programs, real UIKit ownership/clock/title fixtures and the synthetic playback
fixture passed. All seven playback receipt fields are true, including playing/
decoding observation, background/return, account stop, cancellation, teardown and
source encoding. ABI 17, component admission 10, core 9, Foundation 1 and comparison
5 checks passed. Local native host tests passed 55/55. The corrected fixture now
observes the required state; its earlier failed result remains preserved above.

[Linux Actions 43340009221](https://github.com/BananaOnGitHub/Streamside/actions/runs/43340009221)
passed: 224 tests, 220 passed, four existing Apple/donor/Hermes-runner skips.
Documentation validation passed. Local assembly re-admitted the exact donor,
51 Swift boundaries, 11 Objective-C service entries and unchanged 25 runtime probes,
verified every retained donor entry and original HBC, and checked ZIP integrity.
Independent hashing verified both IPAs, modified images, owned frameworks and the
unchanged bundled IVS binary. IPAs remain under the external artifacts directory
and require Feather signing with the same application/keychain identity.
No donor, IPA, certificate or private key was uploaded to Actions.

Static follow-up also confirmed all four generated query/params metadata headers
use imported object/bridge-object value witnesses (`BoWV`/`BbWV`), consistent with
the runtime-checked one-word lowering. ApolloAPI exports the GraphQLQuery protocol;
both Twitch and TwitchKit import the exact Foundation NSString-to-Swift-String
bridge used by the facade. These are ABI/static observations, not network execution.

Reproduction from this source or a proof-compatible documentation-only descendant,
using empty external output locations:

```sh
gh run download 43340009333 --name swiftui-components-2bbfb860e46ac066f83fca870db57370084e730c --dir ../artifacts/ci/2bbfb860e46ac066f83fca870db57370084e730c
python3 tools/native_frontend/components.py verify --output ../artifacts/ci/2bbfb860e46ac066f83fca870db57370084e730c
python3 tools/native_frontend/build.py --donor ../donors/tv.twitch-32.0.ipa --frontend swiftui --components ../artifacts/ci/2bbfb860e46ac066f83fca870db57370084e730c --mode both --output ../artifacts/native-frontend/swiftui/playback-rebuild
```

After component retention expires, rebuild the pinned source workflow. A replacement
assembly has its own hashes; earlier receipts must retain their original identities.
This completes an installable diagnostic candidate after local signing, **not**
physical-device playback acceptance. Authenticated entitlement, visible video/audio,
portrait behavior, actual SDK teardown/performance and zero RN/Hermes throughout
playback still require the device sequence above. Stop at that validation milestone.


## Twitch 32.2 playback latency investigation

The exact 32.2 donor contains Amazon IVS Player 1.59.0 (framework bundle build 1). Twitch's RN-facing native `TwitchIVSPlayerView` has a `lowLatency` property initialized to true, with both initial-buffer override values initialized to zero. Its native property setter and source setup dispatch to IVS's public `setLiveLowLatencyEnabled:`; its buffer helper applies a positive low-latency override using millisecond-scale CMTime when requested. The wrapper also configures network recovery and reads IVS's actual low-latency and live-latency properties. The static defaults do not establish remote configuration, per-stream overrides or realized delay on a device.

Streamside previously let IVS use its inherent settings. The [IVS iOS SDK API reference](https://aws.github.io/amazon-ivs-player-docs/1.56.0/ios/Classes/IVSPlayer.html) documents low latency as enabled by default for compatible streams; the default initial buffer is one second in that mode (two seconds in normal mode). Reducing the initial buffer can worsen stalls and affects startup, not necessarily steady-state delay. `setRebufferToLive:` allows the SDK to recover at the live edge after a stall instead of retaining accumulated delay, at the cost of potentially skipping content. Leave initial buffer duration, network recovery, playback rate, quality selection and the existing source/authorization path unchanged for this experiment.

The native Player settings now include a default-on Low latency preference. Each fresh IVS player reads it before load, enabling both low-latency mode and live-edge rebuffer recovery when on, disabling both when off. A preview-to-theatre promotion reuses the same configured player; no extra load or audio activation is introduced. The five additional Objective-C selectors and their actual signatures are pinned in the 32.2 donor plan. Runtime signatures are checked before invocation; an unavailable boundary leaves SDK defaults in place and records the unsupported configuration. No RN host or new donor hook is introduced.

For device measurement, the adapter samples actual low-latency mode, server-to-player delay and remaining buffered video every two seconds of decoded, unpaused theatre playback. Preview playback and paused/unobserved values are excluded; numeric durations outside 0–120 seconds are rejected. Reports add fixed-size, native-only fields:

- `playback_latency_config`: player configurations [normal, low latency, unsupported] (including previews).
- `playback_rebuffers`: post-playing buffering transitions in theatre [normal, low latency].
- `playback_latency_samples`: two rows [normal, low latency]; each row contains [observations, effective low-latency observations, valid delay count, last delay ms, max delay ms, sum delay ms, valid buffered count, last buffered ms, max buffered ms, sum buffered ms]. A valid count of zero means unobserved, not zero latency. Calculate mean delay as sum divided by valid sample count.

The Apple fixture must verify both policies applied before load, fallback preference behavior on a new player, actual typed duration values and separate telemetry from each mode. Host tests verify numeric bounds, native/original isolation and donor-selector signatures. All 180 Ubuntu checks passed, including the new core telemetry and donor-selector tests. Apple compilation and simulator validation are pending. These are owned fixture/ABI checks, not measured streaming latency. On the iPhone, open the same live stream with Low latency enabled and disabled in separate sessions under similar Wi-Fi conditions, allow it to settle, then export native diagnostics. Compare effective mode, mean/last/max delay, buffer and rebuffer counts; repeat cellular if useful. Server-to-player delay is not full camera-to-screen or chat latency, so compare actual stream/chat responsiveness separately. Do not assert an improvement before physical evidence.


### Verified latency trial candidate

[Apple run 45896447879](https://github.com/BananaOnGitHub/Streamside/actions/runs/45896447879) passed for source `7f68b109896b1a929ee9cb34524a27e845dcb93b` with pinned Xcode 26.6 (17F113), iPhoneOS SDK 26.5. Both new playback receipts (`latency_policy`, `latency_sampling`) and all eight UI coordinate cases passed. The component archive SHA-256 is `c94ad363a99ce965195fab0f71e51ec105235a0e01c37ee170745ed6f8fa6b30`; Ubuntu verification passed.

The locally assembled and hash-verified native IPA is `artifacts/native-frontend/latency-7f68b10/StreamsideNativeProof-Twitch32-native.ipa` (196,650,562 bytes; SHA-256 `c9a55349aece816dc9edb56b127506ea00ba05935de0480658015c9d97eec76f`). The matching component manifest SHA-256 is `178c91b16f1cce2b8b84ed10a572309367aa277d552b6b611137d636329e0b53`, and the proof ID is `014e4aa63d4b14a59160f8fc81e4b6dd4b15e859f3614d3017c7216a49c40501`. The exact 32.2 donor is unchanged. No donor or final IPA was uploaded. Feather signing and actual latency/rebuffer measurements remain device work.


### First physical-device latency comparison (2026-11-27)

The supplied report is from the exact trial candidate; locally retained as `device-validation/native-latency-ab.json` (SHA-256 `bdaf38b2a8dc792c0038307ca6ff71d09143b2386af105fc533c6997510ede81`). Both requested modes configured successfully, with one player created for each, two playing/decoded-frame observations and two adapter releases. No playback errors, post-playing buffering transitions or guarded RN/Hermes/worklet entries were observed, and all three runtime images were armed. The holder count remained 1.

| Requested mode | Samples | Actual low-latency samples | Mean SDK-reported delay | Last delay | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| Normal | 45 | 0 | 4.909 s | 4.937 s | 4.945 s |
| Low latency | 19 | 0 | 5.606 s | 5.610 s | 5.644 s |

The preference reached the configuration path, but IVS did not report effective low-latency mode in either session. There is no observed improvement, and the low-latency recovery-on-rebuffer policy was not exercised because both rebuffer counters are zero. The SDK buffer field also grew to 98.005 s and 42.005 s respectively, unusually close to the session lengths; it cannot be interpreted as trustworthy remaining buffer depth from this evidence alone.

The current low-latency setting is retained. Further controlled testing should isolate playback transport and stream-side support before attempting buffer or rate changes: repeat with low latency requested and the optional playlist-processing feature disabled, using the same stream/network where possible. Compare active-mode samples and SDK-reported delay; the report does not by itself distinguish stream eligibility, playlist characteristics, remote configuration or SDK behavior. No transport or authorization changes are warranted on this evidence.


### Follow-up without optional playlist processing (2026-11-27)

A second export from the same process (launch 123) is stored locally as `device-validation/native-latency-direct.json`, SHA-256 `e585f9a010cb3c54fbb9abd4684fdf2a5f8407b2f3792d8477f1f97f4c9a26d7`. The optional playlist processing was disabled and its cumulative counters did not increase. Exactly one additional player configuration, creation, decoded playing observation and release occurred. The low-latency row added 63 valid delay observations and zero effective low-latency observations, with incremental mean 4.456 s and final delay 4.484 s. Normal-mode counters were unchanged; rebuffer and playback error counts remain zero.

This confirms effective low-latency mode was absent even without the optional playlist processing during this session. An ad break is not required for that comparison. The lower measured delay is a single uncontrolled session difference, not proof of causation. The reported buffer value again reached the 120 s validity ceiling, reinforcing the need to treat that field cautiously. All guarded runtime entries remain zero. The next useful physical check is a stream known to be in low-latency mode in the original client, with the same native preference enabled; this separates stream-side eligibility from client behavior. No source change was made.


### Cross-client comparison and media-delivery negotiation (2026-11-27)

A second anonymized channel was tested against the original RN theatre. In original UI the tester observed a chat message appear in the broadcast overlay after about 3–3.5 seconds; native theatre took at least 5 seconds. This is an informal end-to-end comparison, not a synchronized benchmark. The matching native report is preserved locally as `device-validation/native-latency-second-channel.json` (SHA-256 `6a4bc0865dc2a3328f101e44e13bee9b91571bd4fa8033ab4d848cf5aaa90692`). It records launch 124, one player in each requested latency mode, 51 requested-low observations averaging 5.066 s and 11 normal observations averaging 5.435 s. Effective low-latency observations were zero in both; no playback failures or rebuffering were recorded. The tester described enabling both optional playlist processing and low latency, then disabling both; the export's current optional-playlist preference is enabled, so its cumulative data cannot separately establish that preference for every session. All 24 guarded runtime counts remain zero.

Inspecting the pinned 32.2 HBC (version 98, SHA-256 `ec367e1b2c9fadeacc226a9911c387d6e2322dbcb78d60e6e93857fc234fda47`) offline shows that the original `VideoPlayerComponent` defaults to low latency enabled and no initial-buffer override; `VideoStatsOverlay` reads the native effective low-latency property. The original `buildUsherUrl` includes two media-delivery fields absent from Streamside's URL. The decoded object-literal shape 4756 in that exact function has `fast_bread` set to the string `true` and `player_backend` set to `mediaplayer`. Only these playback capability fields were inspected; no grant, request identity or account data was retained. The original SDK also supports the plain URL load path, so using a private player configuration object or invoking RN is not necessary for this trial.

The native URL builder now supplies the two same media-delivery capability fields for the actual IVS player, in both latency preference modes, leaving the local switch to IVS as in the original implementation. The existing source policy, native authorization, endpoint, quality and mute behavior, optional playlist processing, and player lifecycle are unchanged. The simulator fixture requires the exact six expected query items, including the unchanged synthetic grant encoding and both capability values, and repeats the check with the normal-latency preference. This is a specific candidate correction to the missing negotiation, not evidence that the server will enable low latency. Verify the actual low-latency samples and user-perceived overlay responsiveness on the next device build before tuning further.


### Delivery trial Apple validation attempt 1

[Run 45979369811](https://github.com/BananaOnGitHub/Streamside/actions/runs/45979369811) compiled and linked SwiftUI and passed the synthetic UIKit playback lifecycle/latency/source-encoding fixture. An unrelated coordinate case, `testChatCatchUp`, failed at the five-second XCTWaiter predicate asking whether a static text row was hittable after tapping the catch-up pill. The failure screenshot shows the pill dismissed, the new-messages divider and messages 61–63 visible, with the last row at the bottom of the transcript. The accompanying accessibility snapshot gives the transcript vertical interval 280–784 points, the final row 762–780 points and the marker 697.7–711 points. This evidence shows the catch-up behavior had occurred by the snapshot; it does not retroactively pass the failed assertion.

The coordinate test now verifies actual row geometry for display-only content: the next message must exist, have a nonempty frame contained by the transcript viewport and be within 24 points of its live edge. The visible marker must be contained in the viewport and precede the latest row. The subsequent automatic-follow check uses the same geometry requirement. The real off-center pill tap, dismissal, unread count, scroll preservation, keyboard, delivery and other UI assertions remain required. No production chat code, deadlines or gate receipts are changed. Bounded original failure evidence is retained locally with the build ticket, including `player-input-failure.zip` (SHA-256 `d616aee5c05b1c242f701a87eb3a2cf0d10ce253a34e221c1abce0941b10425a`); the new Apple validation is pending.
