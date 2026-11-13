# Development-only original Twitch cold launch

## Implementation trial

Native development packages offer **Launch original Twitch UI** in diagnostics.
This schedules one future process launch; it never swaps the active root, shuts
an active player down, or reconstructs Twitch startup in a running process.
Fully closing and reopening consumes and synchronously deletes an app-local
boolean before publishing runtime-probe callbacks or selecting the frontend.
The following process returns to Native. Background/foreground does not consume
it. Failed deletion preserves native guards and reports a selection error.

`SSNLaunch` owns frozen selection. `SSNLaunchPreferences` owns app-local storage.
The feature is compiled only into the SwiftUI development native component;
the independent control and preserved UIKit proof have it disabled. Normal
release/Zig application sources do not include this experimental frontend.

The exact-donor eligibility gate now enters a small selector shim. Native returns
false as before; original mode restores registers and executes the original
first instruction then the untouched remainder. It does not force RN eligibility
true. The original server/account configuration may choose legacy native screens;
that does not satisfy a missing runtime positive control. Unpublished selection
traps before donor entry. The selector occupies a validated unused writable DATA
tail word beside the existing observer slot. All 25 runtime probes remain active;
only Native blocks unexpected guarded entries. The independent control retains
its unmodified eligibility gate.

Original mode installs no scene-connect hook, window-root setter, native account
observers, account/feed requests, or native player. It discovers the original key
window after activation for the existing two-finger hold diagnostics gesture.
Feed/image/clock/haptic services are not created during original startup. Opening
diagnostics creates only the diagnostic model/presentation. Reports include
packaged default, actual origin, selection errors/pending status, a stable probe
contract hash, and four native frontend activity counters. Missing counters do
not prove absence. Combined development exports retain native and original
latest/previous reports; the independent control still exports baseline only.

Routine local packaging defaults to one native IPA. Explicit `--mode both`
remains for this one-time control comparison and recoverability. CI continues
building both small owned components; no donor or final IPA enters public CI.

## Playback evidence received before this change

[Unmodified reports and hashes](evidence/playback-device-review-1/manifest.json)
identify Twitch 32.0 build 263110145453907615, exact donor SHA-256
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`,
source `2bbfb860e46ac066f83fca870db57370084e730c`, proof
`06756e9eef1829a5150a3f77e31e4309b89385c5ef3fe3d3ff23b8c28adaf957`.
The user observed stable video/audio on Wi-Fi and a short initial wait/additional
live delay on cellular. No network type or latency was measured by diagnostics.

The latest native report has all four images armed, no failures, all 25 probe
counts zero, nine created players with nine playing and nine decoded-frame
observations, eight releases, and one player still playing at export. Playback
events are `[8,10,9,9,9,8,0,2,7]`. It records no playback failure. The matching
baseline observes RN factory/host/instance, surfaces, bundle load, Hermes engine,
Hermes VMs and worklet VM; positive control is complete. This supports the tested
playback paths without RN/Hermes/worklets. The previous native report is an older
`866bd92` build without playback fields and cannot establish same-build playback
restoration across a restart. Native latest reports 151,472,736 bytes footprint;
baseline latest 279,153,248, at different lifetimes/workloads. These are evidence,
not a controlled memory benchmark.

## Validation boundaries and device checklist

Host selection-policy tests use fake persistence; ARM64 emulation checks both gate
branches at two ASLR slides, general/vector registers, flags, stack, and unselected
trap. Apple CI uses production preference code and window ownership in three
separate simulator processes. These tests have no Twitch donor or authenticated
runtime. Compiler/simulator/packaging results and revisions are recorded separately
below when available. They do not establish actual original Twitch equivalence.

1. Install the combined native IPA with Feather using the existing app identity.
   Open it, check your account/follows and playback, then close the stream.
2. Open Settings → Diagnostics. Choose **Launch original Twitch UI**. Confirm
   that it says the choice is saved. Background and return once: Native must stay.
3. Fully close the app in the app switcher, then reopen. Observe Twitch's original
   startup and navigation. Hold two fingers for one second for diagnostics.
   Exercise normal screens that start RN, then export launch reports. Original
   mode must report origin 2, no pending flag, no native frontend events, no native
   navigation guard, and a complete runtime positive control.
4. Fully close and reopen again. Native must return automatically, recognize the
   existing account, refresh follows and play/close a stream. Export again. All
   guarded runtime counts must remain zero with all probes armed and no failures.
5. For the one-time comparison, export a matching independent control run under
   the same account/device/OS and comparable routing/screens. The retained older
   playback control remains historical reference; it lacks the new hook/contract
   fields and cannot prove their absence. A freshly matching independent control
   is provided for this check only. Installing either replaces the other.
6. Use `python3 tools/native_frontend/compare_launch_modes.py independent.json
   one-shot.json` to check evidence consistency. Observe original routing manually;
   the tool cannot infer it from a zero count. If RN does not start, preserve the
   report and exercise the independently observed positive-control screens; do
   not force RN on or weaken admission.

A unified original launch retains the native package's modern UIKit compatibility
setting and selector shim. It is not binary/pixel identical to the independent
package, nor automatically a valid timing/memory comparison. Compare startup
workloads explicitly. Constructor-to-active time excludes dyld and earlier work.
The independent control remains retained until physical comparison succeeds.
No hot-swap, playback expansion, chat, PiP or mini-player was introduced.

## Initial validation failure

Source `32f7be4d687d08a2471653620f1caa5774a2201c` passed 61 host tests and
[Linux Build](https://github.com/BananaOnGitHub/Streamside/actions/runs/43353156983).
[Apple run 43353157135](https://github.com/BananaOnGitHub/Streamside/actions/runs/43353157135)
failed C compilation because the newly conditional account-observer registration
scoped `account_selectors` away from later notification registration.
[Exact failure and log hash](evidence/one-shot-launch-ci/32f7be4-failure.json)
are preserved. No Apple component or IPA was admitted. The correction shares the
constant selector table at file scope; registration still occurs only in Native.

The prior `2bbfb86` independent control included native account-notification
observers (its report has account events `[1,1,1,0,0]`). It had no native root
ownership guard and observed original RN/Hermes startup. The new matching control
omits those observers as well as the one-shot original launch. Its runtime probe
contract remains the same as the combined package. This intentional isolation
improvement and the delayed diagnostics gesture attachment preclude claiming
identical timing/overhead to the older independently packaged baseline.
