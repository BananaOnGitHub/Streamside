# Native live-list interaction polish

Starts from clean `feat/native-frontend` at `0fb88ea`, compiled source `48fe696`.
The [silent-refresh trial](SWIFTUI_SILENT_REFRESH.md), earlier failed continuity
results and exact package identities remain preserved.

## Device evidence for silent refresh

[Reports and assertions](evidence/swiftui-device-6/validation.json) retain all four
supplied JSON files byte for byte and the original ZIP hash. Matching 48fe696
baseline launch 12 supplies positive RN/Hermes/worklet observations. Native launch
18 is calibrated, armed mask 15, failures zero, all 25 entry counts zero, root
ownership 1 and navigation guard 1. Account/list state 4 returns 100 records at
182998 ms, with two foreground activations and one background transition.

Account events are [2,1,1,0,0], one information update was retained and account-data
clears are zero. This supplies actual same-process lifecycle and retained-update
observations for the prior fix, alongside the user's positive overall feedback.
It is not a video/scroll-position assertion or exhaustive account-state test.
Both previous reports belong to cad1e03 and are excluded from matching-source
restart evidence. No new logout/login sequence is established here. Footprint
101517680 bytes is an uncontrolled snapshot, not a performance benchmark.

## Implementation

Live row vertical padding decreases from five to two points per edge. Existing
metadata ordering, native account/feed path, silent refresh and runtime guards
remain intact. No playback or chat feature is introduced.

Titles now render and measure through the same public UIKit UILabel font/line
layout. Full-height measurement at the actual width is compared with the rendered
one/two-line limit (three at accessibility sizes); length guesses are not used.
Only a measured truncated title offers a long-press preview, hint or VoiceOver
preview action. Title/line-limit changes invalidate old measurement eligibility;
layout changes remeasure. The existing compact frosted popover remains.

An eligible hold waits 150 ms to avoid ordinary taps, then requests a low-sharpness
continuous Core Haptics pattern lasting at most 850 ms, with intensity control
rising from 0.04 to 0.18. Preview opening cancels the ramp and requests one medium
UIKit impact at intensity 0.65. Release, scroll cancellation, loss of eligibility,
row disappearance or app resignation cancels pending/playing feedback. One shared
engine is created lazily after a qualifying hold; start is asynchronous, playback
is haptics-only, auto-shutdown is enabled, and engine stop/reset handlers cancel
old work. No audio-session category is set, and no audio event is included.

Apple documents [hardware capability checks](https://developer.apple.com/documentation/corehaptics/chhapticengine/capabilitiesforhardware()),
[intensity curves](https://developer.apple.com/documentation/corehaptics/chhapticparametercurve),
[haptics-only playback](https://developer.apple.com/documentation/corehaptics/chhapticengine/playshapticsonly),
[engine interruptions](https://developer.apple.com/documentation/corehaptics/chhapticengine/stoppedhandler-swift.property),
and [UIKit impact intensity](https://developer.apple.com/documentation/uikit/uiimpactfeedbackgenerator/impactoccurred(intensity:)).
The ramp is skipped if custom haptics are unsupported; UIKit handles support for
its completion impact. Normalized intensity is not a guarantee of identical motor
strength across hardware, and no device-model calibration is guessed. Physical
feel and cancellation timing require an iPhone; the simulator cannot establish them.

The gear and sheet title are Settings. Account is first; a separate Followed streams
section with heart.fill follows, then Diagnostics. The two-line preference remains
there. The new seven-position discrete slider maps left-to-right to 0.5, 1, 2.5,
3.75, 5, 10 seconds and Off; default index 2 is 2.5 seconds. The selected index is
saved. A single circle expands to 1.5 times the live ring diameter and fades out
per cycle. The base red live ring stays visible. The animation uses a view-local
30 Hz maximum timeline only while visible and UIKit-active; it is removed when
Off, offscreen, inactive or Reduce Motion is enabled. This is a maximum scheduling
rate, not a claim of guaranteed rendering cadence.

[Reduce Motion](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion)
keeps the ring static and disables/greys the cycle selector without changing its
saved value, as requested. It does not disable time updates or the separate tactile
confirmation. No decorative haptic is attached to the repeating beacon.

## Initial validation

Local native checks pass 47/47. Apple CI adds real UILabel truncation fixtures for
short, one/two-line, narrow, emoji/RTL and accessibility-font content, plus public
haptic-pattern construction/duration validation. Pure Swift tests cover the seven
cycle choices, fallback index and cycle math. Existing clock/window fixtures remain.
Component admission requires the new interaction receipts. This does not claim
hardware haptic feedback, exact popover appearance, beacon rendering or gesture
cancellation has been physically tested for the replacement source. Apple build
and final package validation are pending at this implementation checkpoint.


### Apple compiler correction

The first Apple attempt at `786b76a` failed during Swift compilation because the
haptic engine object (not Sendable) was captured into an actor-hop task. The bounded
failure log is preserved in external CI artifacts and
[run 43309340468](https://github.com/BananaOnGitHub/Streamside/actions/runs/43309340468).
No IPA comes from this source. The callback now sends only an object identifier,
a success flag and a generation token to the main actor, which retrieves its own
engine there. Cancellation changes the generation so a late callback for a prior
hold cannot start feedback, including a repeat hold on the same row. Compiler
warnings are not suppressed. Replacement Apple compilation and fixtures are rerun.


## Validated component build and test IPA pair

Compiled/packaged source is `94d2ee3bab41f209a4948d45e3ea35cd700e7329`, after
implementation `786b76a` and the compiler correction above. Exact proof, donor,
IPA/framework/modified-image/manifest hashes, toolchain and receipts are in
[artifact identities](SWIFTUI_LIVE_LIST_POLISH_ARTIFACTS.json). Both final IPAs were
independently rehashed after assembly.

[Apple Actions 43309783839](https://github.com/BananaOnGitHub/Streamside/actions/runs/43309783839)
succeeded with pinned Xcode 26.6 / 17F113, Swift 6.3.3 and iPhoneOS SDK 26.5. Both
frameworks compiled/linked and passed signature verification. Pure Swift model
checks (including cycle mapping/math), real UIKit ownership fixtures, clock
lifecycle fixtures, real-label title measurements and haptic pattern construction/
duration passed in both modes. The simulator does not play or validate a physical
motor, run the user gesture in SwiftUI, or visually inspect the live-ring/settings.
Apple-compiled ABI 12, component admission 9, core 8, Foundation 1 and synthetic
comparison 5 tests passed. Final-source local native checks passed 47/47.

[Linux Actions 43309340559](https://github.com/BananaOnGitHub/Streamside/actions/runs/43309340559)
passed 220 of 224 tests with four explicit skips (Apple Foundation/ImageIO and
missing legacy donor/Hermes-runner prerequisites). This run belongs to feature
source 786b76a. The following correction changes only Apple Swift code and its
investigation record, so the path-filtered Linux workflow did not duplicate that
run. Final-source Apple CI and local native checks passed separately. Documentation
checks pass; public release documentation is unchanged.

Local assembly validated the exact Twitch 32.0 donor SHA-256, all 40 ABI entries,
the unchanged 25-probe coverage, retained donor contents and byte-identical HBC,
then checked output images and ZIP contents. No donor/IPA or signing credentials
went to public CI. Build outputs remain in sibling artifacts, outside the repo.
Both IPAs still need Feather signing with the established application/keychain
identity. These packages have no new physical-device acceptance result yet.

Reproduction (source/proof-compatible checkout; new empty external output):

```sh
gh run download 43309783839 --name swiftui-components-94d2ee3bab41f209a4948d45e3ea35cd700e7329 --dir ../artifacts/ci/94d2ee3bab41f209a4948d45e3ea35cd700e7329
python3 tools/native_frontend/components.py verify --output ../artifacts/ci/94d2ee3bab41f209a4948d45e3ea35cd700e7329
python3 tools/native_frontend/build.py --donor ../donors/tv.twitch-32.0.ipa --frontend swiftui --components ../artifacts/ci/94d2ee3bab41f209a4948d45e3ea35cd700e7329 --mode both --output ../artifacts/native-frontend/swiftui/live-polish-rebuild
```

Actions components expire; rerun the pinned source workflow when needed. Every
new assembly receives its own hashes, without changing earlier artifact identities.

## Physical-device check

1. Sign/install the matching baseline in Feather, open Twitch and export baseline
   reports with the two-finger hold. Replace it with the native IPA using the same
   identity. This source proof requires its own matching positive control.
2. Check slightly tighter live rows and Settings: Account first, followed-stream
   section with a filled heart next, Diagnostics below. Try the two-line toggle.
3. Hold a fully visible short title for one second: expect no preview or hold
   feedback. Find a truncated title: expect a slight progressive rumble followed
   by one distinct tap when its compact popover opens. A title fitting two lines
   must lose that action in two-line mode. Try a title still clipped at two lines.
4. Release a hold early, start scrolling during a hold, scroll the row away, and
   background during one hold. Feedback should stop and no delayed buzz should
   appear afterwards. Check the feel is subtle on this hardware; simulator
   construction tests cannot establish intensity or cancellation timing.
5. Observe one expanding/fading ring around live avatars. Try each of the seven
   slider stops; Off must leave a static red ring. Enable system Reduce Motion:
   expect static rings and a greyed, nonadjustable cycle slider. Disable Reduce
   Motion and confirm the saved choice returns. No haptic should repeat with a ping.
6. Refresh, background/return and fully close/reopen. Verify content stays present
   on ordinary return, timers still work and the cycle preference persists. Export
   before close and after reopening, keeping all latest/previous files. Require
   calibrated/complete probes, root ownership 1, zero failures and zero guarded
   RN/Hermes/worklet entry counts. Preserve evidence if any check fails.

The prior 48fe696 snapshot establishes its observed silent refresh and zero runtime
entries only; it cannot stand in for this replacement's animation/haptics/gesture
or lifecycle acceptance. Broader authentication-provider, invalid-session and
account-switch device coverage is not expanded by this UI-only change.
