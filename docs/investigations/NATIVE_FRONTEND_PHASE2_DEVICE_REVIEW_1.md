# Native frontend — first signed-in device review

## Evidence and identity

The supplied `nativetesting.zip` contains six JSON reports (five distinct byte sequences); `baseline-latest 2.json` and `baseline-latest 3.json` are identical. These are user-supplied device exports, not locally executed iOS tests. Preserve the [original archive](evidence/native-frontend-device-1/nativetesting.zip), [individual report hashes](evidence/native-frontend-device-1/hashes.json), and [comparison output](evidence/native-frontend-device-1/comparison.json).

- Tested source: `f5a6c8e10a98d14b35d459648f5278fb990f5b58` on `feat/native-frontend`.
- Proof: `7781ed12b1ec49cc4be32cef34f946f8515da95754c59fd679af690d67abafe9`.
- Donor: Twitch 32.0, build `263110145453907615`, IPA SHA256 `076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
- Reported hardware: `iPhone17,1`; kernel: `27.0.0`. No exact iOS marketing version or installed re-signed IPA hash was supplied.
- Original unsigned package identities remain in [the original artifact receipt](NATIVE_FRONTEND_PHASE2_ARTIFACTS.json). Re-signing changes package bytes; exports establish embedded source/proof identities, not installed IPA hashes.

The user reports that the native build briefly shows the Twitch logo splash, then opens the UIKit menu. They also report that the baseline's floating Diagnostics button obscures Settings in the profile menu, preventing normal sign-out. No screenshot or explicit confirmation that the displayed account/channel names match the expected account accompanied these exports; names are deliberately absent from diagnostic reports.

## Observed results

Every supplied report has all four image observers armed (`armed_mask=15`), the expected 25 probe keys, matching donor/proof/source identity, and no recorded failures. The baseline positively observes RN and Hermes startup, including a worklet runtime: RN factory/host/instance each 1, root surfaces 2, script load 1, Hermes runtime/implementation/engine each 2, evaluation paths each 11, and worklet runtime 1. The baseline positive control is complete. Its unused alternate factory paths remain at zero; that does not independently exercise every possible donor path.

All 25 probe counts are zero in every native export, including the optional native holder count. Both native launches report account/list state 4 (followed channels loaded), 50 results, and matching baseline calibration. This establishes successful execution of the native account-plus-follow-list request path as reported by the candidate. The privacy-safe report does not contain the username or channel identities, so their visible correctness still needs the tester's confirmation. No public endpoint or fixture is substituted by this path.

The first native process was exported at about 128 seconds, then preserved as `native-previous.json` at about 141 seconds with three active notifications and two background notifications. The second native process (`native-latest 2.json`) was exported at about 93 seconds with launch sequence 2 and two active notifications. All guarded counts remain zero across both processes. Notifications can include effects of modal/system UI; they are not exact counts of deliberate Home Screen cycles.

The existing comparison tool passes using `baseline-latest 2.json`, `native-latest 2.json`, and `native-previous.json`, with no consistency failures. It establishes the recorded launch/background/foreground/reopen sequence. Reports do not include a manual refresh counter; successful completion after each of the two requested manual refreshes remains a tester observation. Neither signed-out/invalid-session handling nor account switching has been exercised in the supplied evidence.

The splash is compatible with preserving Twitch's native launch setup and launch resources. A static logo is not evidence of React Native execution. The positive baseline and zero instrumented native runtime-entry counts are the relevant runtime evidence; this does not establish absence of mapped React/Hermes libraries or all native static-initializer overhead.

## Measurements

| Metric | Baseline exports, same process | Native process 1 | Native process 2 |
| --- | --- | --- | --- |
| Physical footprint at export | 315.3–320.7 MiB | 50.1–54.3 MiB | 50.0 MiB |
| Peak observed footprint | 315.3–320.7 MiB | 60.6 MiB | 59.9 MiB |
| Constructor to first active | 642 ms | 476 ms | 297 ms |
| Constructor to diagnostic scaffold ready | 450 ms | 371 ms | 234 ms |

The latest baseline/native snapshot difference is 283,787,672 bytes (about 270.6 MiB, 84.4%). These are encouraging individual samples, not a controlled benchmark. Foreground dwell and UI histories differ; only one baseline process was supplied. Peak means sampled peak, not an OS lifetime high-water mark. Timing excludes dyld and work before the diagnostic constructor, and does not measure splash duration or account/list readiness. Retain the raw values instead of presenting these as full cold-launch improvements.

## Obstruction fix and remaining acceptance

The original baseline placed a fixed button at `(16,64,130,44)` and repeatedly brought it to the front. That blocks a real Twitch account control and prevents completing the signed-out test. The revision removes the overlay entirely. Holding two fingers still for one second opens Diagnostics; normal one-finger taps are neither covered nor delayed/cancelled by this recognizer. The callback presents once on the gesture's began state and uses the currently presented controller so Diagnostics can be reached from a modal profile/settings screen. Return to Twitch dismisses it.

This is a small frontend access change. Donor patches, ABI admission, native requests, runtime guards and numeric report schema are unchanged. The source/proof identity changes, so the replacement baseline/native pair needs fresh matching calibration. The gesture and presentation behavior require physical-device verification; compilation and host emulation do not establish that UIKit interaction works on the phone.

Next device steps: install the revised baseline over the existing app using the same signing settings; use Settings normally; open Diagnostics with the two-finger hold and save a fresh positive-control report. Preserve earlier signed-in reports before signing out through Twitch normally. Install the matching revised native build over it, confirm no authorized session and no stale account/follows, background/reopen and fully restart, then export. The authenticated comparison tool intentionally rejects signed-out account state; use the signed-out checklist and the individual report fields rather than treating that rejection as a runtime-isolation failure. Signed-in account/channel identity and manual refresh observations can be supplied in text without sharing names or credentials.

This review supplements the [original Phase 2 report](NATIVE_FRONTEND_TWITCH_32_PHASE2.md) and [original validation receipt](NATIVE_FRONTEND_PHASE2_VALIDATION.json), whose pre-device-testing scope is preserved. Updated build/check identities belong in a separate follow-up receipt.

## Replacement package receipt

Source revision: `2308ca8648fd2ffc7bcfd199ddfda9497b7594ca`. Replacement proof: `39cee54065c6e419657af64480dbcf0397e0fca83f64e28c5f2afb080a5217f0`. Both flavors were compiled with Zig 0.14.0, passed donor/ABI/probe admission, retained-entry verification and ZIP verification, and require the usual device-authorized re-signing. They are in `build/native-frontend-gesture-v2/`, leaving the original candidate files intact. The [follow-up receipt](NATIVE_FRONTEND_PHASE2_GESTURE_V2_ARTIFACTS.json) records exact identities, hashes, build command and validation limits. All 23 existing native frontend host tests passed with no skips; the legacy suite was not repeated for this frontend-only control change. The replacement gesture and signed-out sequence have not been exercised on iOS here.

| Flavor | Bytes | Unsigned IPA SHA256 |
| --- | --- | --- |
| Baseline | 196413112 | `17797cdcb62f39c7fca51a6f99d6e79de03d24dda7633fce84d3538f23e96c2d` |
| Native | 196417366 | `ebd3510e05d979693dbd38037ce8d0d3dd172722e5876fac293da6f21fec1926` |
