# Preview dismissal work and cold audio setup

2026-11-17. Branch `feat/native-frontend`, starting from `6619d9f`.
The [5ada9ea package](SWIFTUI_PREVIEW_UNBLOCKED_RETURN_VALIDATION.json) passed Apple
and local package validation. Its [device review](SWIFTUI_PREVIEW_UNBLOCKED_RETURN_DEVICE_REVIEW.json)
confirms unblocked return functionality, but reports a frozen delay before closing
and external media interruption only on the first preview after process launch.
The exact raw report is private in the package's device-review directory.
It matches the delivered source/proof/donor, with zero failures, playback errors,
mute mismatches and runtime probe hits, native root ownership, 100 channels and
one background event. It contains no stage timings or audio-session observations;
it does not attribute either defect. Baseline calibration remains false.

## Findings and change

The old user-dismissal path synchronously captured the composed video/details
view, stopped IVS, detached and destroyed the player, deactivated/restored audio,
and fsynced diagnostic output before starting its return animation. Source review
identifies these possible blocking operations; the device export does not time
them individually. Removing the overlay's hit-test ownership did not remove this
main-thread work.

The whole-preview snapshot is removed. Return reuses the already retained source
thumbnail artwork immediately, avoiding a GPU snapshot during the dismissal input
handler. Its critically damped 0.52-second animation, moving-source adjustment,
early input release, directional swipes and Reduce Motion fallback are unchanged.
Media cancellation still happens immediately; the closing visual owns no player.

IVS pause and view detachment remain on main, along with all other SDK calls and
UIKit work. The existing owned player reference is transferred to a serial disposal
queue for its final release. The donor IPA was rehashed before inspection: Twitch 32.0 build
263110145453907615, SHA-256
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
Its AmazonIVSPlayer Info.plist identifies
version 1.58.0, semantic build `1.58.0-rc.2-ultralight.1`, image SHA-256
`f6bbfbf4ab295778e431f44e3ba8d242d9f3681e27d1413280db095bad85b4c5`.
Amazon explicitly allows off-main IVSPlayer deallocation starting in
[iOS SDK 1.45.0](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/release-notes.html).
Its [thread-safety guidance](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/ios-getting-started.html)
still requires creation and player API calls on main. No new private SDK method,
Swift layout, donor hook, SDK upgrade or playback request was introduced.

A separate serial queue owns audio configuration and restoration. Preparation is
asynchronous, and only an admitted main-queue completion starts the original native
GraphQL request and touches the cold SDK classes. A generation and cancellable audio
state prevent stopped, backgrounded or account-invalidated preparation from later
creating a request/player. Each retirement queues restoration before any subsequent
facade's setup. It restores only a still-matching installed category/mode/options,
preserving a changed external owner. SDK disposal cannot block that audio queue.
Explicit Watch promotion alone waits for its audio-policy upgrade, as part of
entering the actual theatre; it retains the same request/player and mute ordering.

Silent previews now use Ambient/Default without an explicit audio-session
activation. Apple's [Ambient category](https://developer.apple.com/documentation/avfaudio/avaudiosession/category-swift.struct/ambient)
mixes other apps' audio inherently. This is installed before the first SDK
compatibility lookup/creation, rather than activating Playback/MoviePlayback with
MixWithOthers immediately before load. Theatre uses the existing exclusive
Playback/MoviePlayback policy only after an explicit stream opening or Watch.
This addresses the owned first-preview activation path; it does not establish that
all first-preview external audio is preserved on the phone. That requires retesting.

Playback-triggered diagnostic writes are now coalesced onto a utility queue. Late
updates schedule another write; exporting diagnostics still produces a fresh report.
Runtime guard failures retain their original synchronous evidence-and-stop path.
The RN/Hermes/worklet probes, startup guards, auth/session handling and original
one-shot frontend selection are unchanged.

## Bounded timing evidence

The report adds `playback_work_us`, five rows of `[count, last_us, maximum_us]`:

| Row | Work measured |
| --- | --- |
| 0 | Main-thread IVS pause |
| 1 | Main-thread player/view detachment |
| 2 | Background final SDK release |
| 3 | Background audio-policy preparation or promotion |
| 4 | Background audio restoration attempt |

Durations use monotonic process uptime and are clamped to 60,000,000 microseconds.
Unknown stage indices are ignored. Count zero means unobserved, not measured zero
work. There are no account identifiers, URLs, credentials, other-app identities or
audio samples. Host coverage checks count/last/max, bounds and separation from
runtime probe evidence. These stage timings are not end-to-end frame benchmarks.

## Validation

The strengthened mandatory Apple playback fixture starts cold in a nonmixing
category, observes Ambient at the first synthetic IVS initialization and both
preview loads, and requires zero explicit activation calls before Watch. It retains
mute-before-load, same-player promotion, local controls, source encoding, background
resume, account invalidation, pending-promise cancellation and teardown checks.
It additionally cancels queued audio preparation and requires no late request.

The synthetic SDK destructor requests a real main-queue heartbeat while disposal
is in progress, then deliberately sleeps 200 milliseconds on its worker. Stop must
return within 100 milliseconds, the heartbeat must run while disposal is pending,
actual deallocation must finish off-main, and playback diagnostic writes must not
run on main. The fixture waits for both real final release and the recorded audio
restoration attempt before checking restored category/mode/options. Component
admission requires `preview_cold_audio`, `async_retirement` and
`audio_preparation_cancellation` and `audio_retirement_ordering`; missing evidence
fails. The ordering case immediately starts a second preview while the first
player retires, then requires Ambient/mute to remain in effect after the old SDK
object has actually been disposed and restores the original audio policy only
after the second preview stops.

Host validation: all 82 native frontend tests passed (9.285s), including timing
bounds and rejection of missing new audio/retirement receipts. All 12 provider
routing tests passed. Updated Python tooling compiled with bytecode routed to a
temporary directory. Host logs remain outside the repository under the matching
validation artifact folder. Documentation and whitespace checks are required
before commit.

All prior real decoded-video/clipping, source animation, swipe, gesture, ownership,
player-control/pixel, networking and launch-selection gates remain mandatory.
Apple-specific checks and physical-device results for this change are pending.
Synthetic audio policy tests cannot establish interruption behavior in another app.
No new IPA or successful Apple result is claimed at implementation time.

Device review after a successful Apple build: start music or a podcast, fully close
and reopen Streamside, then open its first preview. Check uninterrupted external
audio and silence in the preview; dismiss by outside tap and swipe, looking for an
immediate return. Repeat several previews, then Watch to confirm intentional audio
takeover and same-player playback. Review rapid close/reopen, scrolling during
return and background/account cancellation, and export Native diagnostics afterward.

## Successful Apple build and local package

Source `54ff64b3e4fa21bc09d19cdc9d1aee1e857872ee` passed the
[Codemagic build](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afd0e43d133a39c4a1279f5).
The [validation record](SWIFTUI_PREVIEW_LIFETIME_AUDIO_VALIDATION.json) retains
the toolchain, receipts, stage times and component/package hashes. All four new
playback receipts passed, including cold audio admission, responsive retirement,
preparation cancellation and ordered restoration across overlapping previews.
The four coordinate UI tests passed, including actual decoded video clipping,
source return, scrolling/hold cancellation, directional dismissal and both styles
of player animations. All 60 post-download ABI, component, core, launch, probe
and comparison checks passed.

Ubuntu assembled and verified the IPA locally against the exact donor, including
all retained donor entries and unchanged original HBC. The package is retained
outside the repository at
`artifacts/native-frontend/preview-lifetime-audio-54ff64b/`. It requires local
Feather signing with the existing application/keychain identity. No donor or
signing material was uploaded to CI; no VM was used. This establishes compilation,
simulator behavior and successful packaging, not physical-device acceptance.
The device checks above remain pending. The earlier pending statement describes
the implementation-time evidence; this is its successful build follow-up.
