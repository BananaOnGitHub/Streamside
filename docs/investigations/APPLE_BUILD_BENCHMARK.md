# Apple build environment timing trial

Compare one execution of the accepted shared-travel source `28eb9bc800865373e906ed28eab0f885ccc97331` on GitHub Actions, Codemagic and the optional Tahoe VM. Ubuntu remains the authoritative source/history and packaging workspace. This trial does not change the primary build environment.

The Actions reference is [Native SwiftUI run 43658504705](https://github.com/BananaOnGitHub/Streamside/actions/runs/43658504705). Compare native and original-startup component compilation/linking, model tests, synthetic UIKit/simulator tests, the two player coordinate tests, Foundation HTTP integration, logger tests and report-comparison tests. Separate queue/provisioning/checkout time from the Apple workload. The downstream Linux ABI job is outside the Apple-worker comparison.

[Codemagic configuration](../../codemagic.yaml) is manual-only, uses Mac mini M2 and requests Xcode 26.6. It fetches the exact reference source into a detached worktree and uses the existing component builder, including its strict Xcode build/SDK checks. No donor, signing identity, credentials or device diagnostic export is an input/artifact. Outputs stay outside the source checkout. The configuration revision is recorded separately from the compiled source. No project cache restoration is configured.

The VM preflight confirms Xcode 26.6 build 17F113, Swift 6.3.3 and iPhoneOS SDK 26.5, with the iOS 26.5 simulator runtime. It is x86_64 with 16 visible CPUs and approximately 12GB memory; hosted Apple-silicon machines are a different hardware/virtualization class. Transfer only allowlisted owned worker/test inputs, not Git history or the donor. The VM uses the same native/baseline worker and auxiliary tests, with a fresh output workspace and simulator. Transfer results back to Ubuntu, then remove only this trial's VM workspace. Logs retain individual command durations and failure evidence.

Treat these as single-run observations, not statistical rankings or uniformly cold-cache measurements. A fresh project output does not erase machine-level compiler or simulator caches. Report incomplete/failed test workloads separately; a fast failed run is not a successful speed comparison. Execution and measured results are pending.

Codemagic configuration references: [workflow syntax and manual triggering](https://docs.codemagic.io/yaml-basic-configuration/yaml-getting-started/), [Xcode 26.6 image](https://docs.codemagic.io/specs-macos/xcode-26-6/).
