# Apple build environment timing trial

Compare one execution of the accepted shared-travel source `28eb9bc800865373e906ed28eab0f885ccc97331` on GitHub Actions, Codemagic and the optional Tahoe VM. Ubuntu remains the authoritative source/history and packaging workspace. This trial does not change the primary build environment.

The Actions reference is [Native SwiftUI run 43658504705](https://github.com/BananaOnGitHub/Streamside/actions/runs/43658504705). Compare native and original-startup component compilation/linking, model tests, synthetic UIKit/simulator tests, the two player coordinate tests, Foundation HTTP integration, logger tests and report-comparison tests. Separate queue/provisioning/checkout time from the Apple workload. The downstream Linux ABI job is outside the Apple-worker comparison.

[Codemagic configuration](../../codemagic.yaml) is manual-only, uses Mac mini M2 and requests Xcode 26.6. It fetches the exact reference source into a detached worktree and uses the existing component builder, including its strict Xcode build/SDK checks. No donor, signing identity, credentials or device diagnostic export is an input/artifact. Outputs stay outside the source checkout. The configuration revision is recorded separately from the compiled source. No project cache restoration is configured.

The VM preflight confirms Xcode 26.6 build 17F113, Swift 6.3.3 and iPhoneOS SDK 26.5, with the iOS 26.5 simulator runtime. It is x86_64 with 16 visible CPUs and approximately 12GB memory; hosted Apple-silicon machines are a different hardware/virtualization class. Transfer only allowlisted owned worker/test inputs, not Git history or the donor. The VM uses the same native/baseline worker and auxiliary tests, with a fresh output workspace and simulator. Transfer results back to Ubuntu, then remove only this trial's VM workspace. Logs retain individual command durations and failure evidence.

Treat these as single-run observations, not statistical rankings or uniformly cold-cache measurements. A fresh project output does not erase machine-level compiler or simulator caches. Report incomplete/failed test workloads separately; a fast failed run is not a successful speed comparison. Execution and measured results are pending.

Codemagic configuration references: [workflow syntax and manual triggering](https://docs.codemagic.io/yaml-basic-configuration/yaml-getting-started/), [Xcode 26.6 image](https://docs.codemagic.io/specs-macos/xcode-26-6/).

## Observed results

All runs used the same component source and pinned Xcode build/SDK. The [bounded results and evidence hashes](APPLE_BUILD_BENCHMARK_RESULTS.json) retain provider identities, exact timings, validation limits and cleanup outcome. Raw logs, transferred-input archives and outputs are outside the repository under `../artifacts/benchmarks/apple-28eb9bc/`.

| Measurement | GitHub Actions | Codemagic M2 | Intel Tahoe VM |
| --- | ---: | ---: | ---: |
| Native SwiftUI compile | 13.0s | 9.6s | 10.2s |
| Native + original-startup components and their simulator suites | 18m 12.0s | 10m 15.5s | 16m 41.1s |
| Whole hosted Apple job/build | 18m 49s | 11m 00s | No uninterrupted total |
| Final required checks | Passed | Passed on runner | Passed after auxiliary recovery |

The [Codemagic trial](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6af942e690e83b09c4fa7473) used configuration commit `567b2276e6e10c46b12d7ce790e7ff1de6693f26` and compiled the detached reference source. Machine preparation was 23s, checkout 3s and preparation of the pinned worktree 1s. Its timed workload was displayed as 10m 27s. The log reports component build/admission 615.498s, Foundation 8.018s (one test) and comparisons 0.067s (five tests), all exit zero. The live compile log reported native SwiftUI 9.6s. Existing component admission explicitly completed on the runner, checking all required simulator/UI receipts and hashes.

Codemagic's component workload was approximately 44% shorter than Actions in this trial. Swift compilation itself is a small part of the suite; simulator startup, installation, harness building and UI automation dominate the total. The Codemagic timer includes component preparation/admission while the Actions/VM component sums use the two worker durations. This small scope difference is retained rather than presented as identical measurement boundaries. Different machines and pre-existing caches prevent a statistical or universally cold-cache ranking.

The in-app browser blocked the artifact-storage host with `ERR_BLOCKED_BY_CLIENT` when attempting the provided download. No bypass was attempted. The final runner log and completed build page were preserved, but Codemagic's downloadable artifact hashes/binaries were not independently checked on Ubuntu. A screenshot of the successful overview is retained outside Git with its hash. No account email, signed download URL, credentials or private keys are in the committed evidence.

## VM recovery, validation and cleanup

The VM's native worker passed in 804.121s and the original-startup worker in 196.997s. The native coordinate tests passed both glass/plain cases, including all-region shared travel and real intermediate-opacity pixels. The live collection connection ended after these passes; the auxiliary phases recorded `Broken pipe`. These component builds were not repeated.

Detached auxiliary recovery first exposed a header omitted from the transfer allowlist. The Foundation harness extracts production code that includes transitive cache headers; scanning only the fixture's initial includes missed them. Twelve existing include dependencies were added without changing any production source or test. The complete Foundation test then passed in 7.197s; all five report-comparison tests passed separately. The interrupted receipts and the missing-header failure remain in the recovered evidence. This is not reported as an uninterrupted full-suite pass or as a platform regression.

The recovered VM outputs were wrapped in standard component metadata on Ubuntu and passed existing complete source/toolchain/receipt/hash admission. All 17 ABI emulation tests passed against the VM's Apple-compiled object. An initial Ubuntu import failure from omitting the existing Unicorn dependency path is retained separately; the corrected run used the already installed pinned dependency. Admission/emulation and transfer overhead are outside the VM's Apple worker durations.

Only the allowlisted owned sources and fixtures were transferred to the VM, including the supplemental header closure. No Git database or donor was transferred. Both trial simulator IDs were confirmed absent, the created temporary VM workspace was removed after recovering the outputs, and cleanup evidence was retained. GitHub Actions remains the primary environment. Codemagic is available as an explicitly manual timing workflow; there are no automatic triggers, signing integrations or release publishing in its configuration.

## Routing follow-up

The subsequent [Codemagic-preferred routing trial](APPLE_BUILD_ROUTING.md) replaces
the fixed-source benchmark workflow with current-source builds and records
successful Ubuntu API retrieval/verification of the original benchmark artifact.
The measurements and original download limitation above remain historical.
