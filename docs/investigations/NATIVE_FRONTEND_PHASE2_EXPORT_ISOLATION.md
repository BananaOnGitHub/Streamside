# Native frontend — separate baseline and native exports

## Problem and cause

After the gesture-access replacement, the tester reported that the baseline export included native JSON logs. The original exporter explicitly attached all four retained report filenames from the shared application container. It wrote a fresh report for the running flavor, then included saved reports from both flavors. The original behavior was intended to recover native failure evidence through the baseline, but made an ordinary baseline export ambiguous. The presence of native files in that export alone does not establish that the baseline generated native telemetry or launched the native frontend.

This follow-up changes the export selection only. A baseline Export report action attaches `baseline-latest.json` and an existing `baseline-previous.json`. A native export attaches `native-latest.json` and an existing `native-previous.json`. The selection is compiled for the running flavor, and the action description identifies which reports it shares. Saved reports are neither renamed nor deleted. No cross-flavor recovery action is added.

Runtime guards, probe definitions, donor admission, account/list services, report contents and calibration rules are unchanged. The [original signed-in evidence](NATIVE_FRONTEND_PHASE2_DEVICE_REVIEW_1.md) and original packages keep their identities. New source content changes the proof identity, so replacement baseline and native packages must be used together with fresh baseline calibration.

## Validation and device check

Build both flavors from a clean committed `feat/native-frontend` checkout using the exact Twitch 32.0 donor and Zig 0.14.0:

```sh
python3 tools/native_frontend/build.py --donor /home/bananas/Agent-Stuff/streamside/donors/tv.twitch-32.0.ipa --zig build/toolchains/zig-0.14.0/zig --mode both --output build/native-frontend-export-v3
```

Packaging checks include exact donor/ABI admission and retained-entry verification. Each resulting framework is inspected to confirm that its own two complete export filenames are present and the opposite flavor's complete filenames are absent. This is static verification of selection, not execution of the iOS share sheet. No new tests are added for this small export-list correction; the unchanged host suite and normal documentation checks are run.

On device, install the replacement baseline over the current app with the same signing settings, open Diagnostics with the two-finger hold and export a fresh positive-control report. Only baseline files should be offered, even if native reports already exist in the container. Sign out through Twitch's normal Settings, install the matching native replacement over it, and export after the signed-out restart checks. Only native files should be offered. Preserve the two exports separately; comparisons need the separately saved baseline report.

The revised export cannot recover native JSON through the baseline if the native app cannot reach its own Export action. The native reports remain retained locally. Preserve the iOS crash report and report that access limitation; do not interpret an inaccessible native report as zero activity. [Device instructions](NATIVE_FRONTEND_PHASE2_DEVICE_TEST.md) describe this limit.
