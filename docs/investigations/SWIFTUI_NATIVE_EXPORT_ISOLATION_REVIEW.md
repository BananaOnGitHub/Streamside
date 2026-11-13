# One-shot launch device review and export isolation correction

## Device evidence

[Attachment identities and duplicate mapping](evidence/one-shot-device-review-1/manifest.json)
preserve ten supplied JSON entries as eight distinct unmodified reports. Two
pairs are byte-identical duplicates. Other similarly named files are different
snapshots or older source revisions; filenames alone do not establish origin.
All new launch-selector observations identify source
`1ca14140a6a711ff408d23eac674067d0d27ccab`, proof
`ca8bc843409197a3c17d0d88f07a4efb8f2a785c10ad6aae0da51d9a6da27ea5`,
Twitch 32.0 build 263110145453907615, donor SHA-256
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`,
iPhone17,1 and kernel 27.0.0. The reports contain no account or channel names,
credentials, request content or media.

| Process | Observation |
| --- | --- |
| Independent original 17 | Origin 0, packaged native false, selector disabled, original root, no native frontend events/guard/requests/player, complete runtime positive control. |
| Native 23 | Origin 1, original launch pending true, native root/guard, 100 follows, foregrounds 3/backgrounds 2, all 25 probe counts zero. |
| One-shot original 18 | Origin 2, packaged native true, selector enabled, pending false, original root, no native frontend events/guard/requests/player, complete runtime positive control. |
| Native 24 | Origin 1, pending false, native root/guard, authenticated list state 4 with 100 follows, all 25 probe counts zero and matching baseline calibration. |

All four have armed mask 15 and zero failures; new-format reports have selection
error zero. Independent 17 and one-shot 18 use the same probe contract. Both
observe RN factory/host/instance 1, bundle load 1, Hermes runtimes 2, Hermes
engine entries 2 and worklet runtime 1. One-shot observed three surfaces versus
two in the independent control; all required runtime paths were observed in both.
Its four native frontend activity counters, five account-event counters, five
navigation-event counters and nine native playback-event counters remain zero.

[Strict comparison results](evidence/one-shot-device-review-1/comparison.json)
pass both original-mode report consistency and Native background/reopen report
consistency. These establish reported selection, runtime coverage, root ownership,
flag consumption, automatic Native return and successful authenticated listing.
They do not prove identical routing screenshots, every original authentication
path, or an identical workload/performance benchmark. No screen recording or
explicit routing walkthrough accompanied this attachment. Existing modern UIKit
styling and selector-shim differences remain as recorded in the original trial.
The native process sequence uses a separate counter namespace from baseline;
therefore 23/18/24 are not a single global sequence. Origin, source, consumed flag
and matching proof distinguish the reports; the user-supplied sequence remains
necessary to order modes across processes.

The two older reports identify `2bbfb86` and its distinct proof and are retained
as history. Its final Native playback snapshot has ten created, playing,
decoded-frame and released players, nine opens/closes, no playback errors, and
all probes zero. It must not be treated as playback validation of `1ca1414`:
that build's attached Native reports have no playback activity.

## Export regression and correction

The initial one-shot implementation exported both native and baseline report
pairs from the combined package. That regressed the earlier mode-isolation
behavior and made repeated sharing difficult to sort. The backend continued
writing mode-separated files correctly; the share-list selection was wrong.

The bridge now chooses only the frozen current process mode. Native exports
`native-latest.json` and `native-previous.json`; original mode exports only
`baseline-latest.json` and `baseline-previous.json`, whether entered from the
one-shot selector or the independent control. The button says **Export native
reports** or **Export baseline reports** accordingly. Scheduling the next launch
does not change the current export mode. Existing reports/calibration are retained
on device; opposite-mode reports are excluded from sharing, not deleted.
The one-shot preference, eligibility shim, runtime guards, account/playback and
navigation ownership code are unchanged.

No new abstraction or implementation-mirroring test was added for this small
share-list correction. Existing native host tests and full Apple compilation,
simulator, component/ABI/core/comparison checks are the validation gates. Actual
share-sheet contents after the correction still require a physical device.

Install the corrected Native IPA with Feather using the existing app identity.
Export once in Native: only native-named reports should appear. Schedule original,
fully close and reopen, then hold two fingers for one second to export there:
only baseline-named reports should appear. Fully close/reopen to return to Native.
No fresh independent baseline package is required for this export-only fix.

## Relationship to earlier records

[The original one-shot launch trial](SWIFTUI_NATIVE_ONE_SHOT_LAUNCH.md) and its
[artifact identities](SWIFTUI_NATIVE_ONE_SHOT_ARTIFACTS.json) describe the earlier
mixed-export build and remain unchanged. This record supersedes only that export
behavior and updates the device evidence; it does not rewrite its prior outcome.
Corrected source, CI results and the single replacement package are recorded
below after validation and packaging.

## Corrected build

Source `83c71dc3de3712f782bdc5beb3d8b22811edfee3` passes 61 native host tests and
[Apple CI run 43360120437](https://github.com/BananaOnGitHub/Streamside/actions/runs/43360120437):
Xcode 26.6 build 17F113, Swift 6.3.3, iPhoneOS SDK 26.5, target arm64 iOS 16.4.
Both owned components compiled/linked and passed model, UIKit ownership, clock/title,
synthetic playback and three-process preference/root-selection fixtures. Downstream
Apple ABI (17), component admission (11), native core (9), launch policy (1),
probe emulation (6), original-launch report comparison (3), existing comparison
(5), and Foundation HTTP (1) checks passed. No separate Linux/Zig workflow was
triggered: this correction changes only SwiftUI native bridge/presentation code
and development evidence. Documentation validation passed locally and in CI.

[Exact package identities and validation receipts](SWIFTUI_NATIVE_EXPORT_ISOLATION_ARTIFACTS.json)
identify the single replacement Native IPA. Local packaging validated the exact
donor, 51 Swift ABI entries, 11 Objective-C services, 25 probe sites, archive
integrity, retained HBC/backend entries and inserted component identity. All
outputs remain outside the repository. No donor, credentials or signing material
were sent to CI. Install/re-sign through Feather as before. The independent
`1ca1414` control remains suitable for the same probe-contract comparison; no
replacement baseline IPA was generated.

Reproduce with a clean compatible `feat/native-frontend` checkout and the exact
donor outside the repository:

```sh
gh run download 43360120437 \
  --name swiftui-components-83c71dc3de3712f782bdc5beb3d8b22811edfee3 \
  --dir ../artifacts/ci/83c71dc3de3712f782bdc5beb3d8b22811edfee3
python3 tools/native_frontend/components.py verify \
  --output ../artifacts/ci/83c71dc3de3712f782bdc5beb3d8b22811edfee3
python3 tools/native_frontend/build.py \
  --donor ../donors/tv.twitch-32.0.ipa \
  --components ../artifacts/ci/83c71dc3de3712f782bdc5beb3d8b22811edfee3 \
  --output ../artifacts/native-frontend/swiftui/export-isolation-reproduction
```

Use an empty output directory and the recorded source revision or compatible
documentation-only descendant. Source/input admission rejects incompatible
components. If Actions artifacts expire, rebuild owned components at the pinned
Apple toolchain. The source proof changes with this bridge correction, so a new
original-mode positive control calibrates subsequent Native launches. This does
not require installing another independent baseline IPA.

Host/CI success and packaging do not verify the corrected device share sheet.
The checklist above is the remaining device check for this small correction.
