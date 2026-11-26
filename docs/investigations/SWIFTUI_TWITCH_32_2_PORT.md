# Twitch 32.2 native frontend port

## Identity and scope

The native frontend's previously device-tested Twitch 32.0 implementation is preserved at commit `b2e1646b3d3f0dc091fbc4666d0bc5038c032e9a`. Its donor and working chat-polish IPA remain in the local workspace as rollback inputs.

The new target is the locally supplied Twitch 32.2 IPA, bundle `tv.twitch`, build `263241857361451067`, minimum iOS 16.4. Donor SHA-256: `42b5d35b3e3421dc099293e9c577f7b007025de41deed30ab6dd79440fc84f40`.

The donor and packaged IPA remain local; CI compiles only owned components. Existing SwiftUI features and settings remain unchanged. The admission contract now pins the exact 32.2 donor rather than accepting a version range.

## Integration findings

- The donor's Mach-O images and native service addresses changed. The React and Hermes executable code sections remain identical to 32.0, while Worklets is now integrated into the main executable rather than a separate framework. The admission plan and probe-image accounting reflect the move, preserving all 25 diagnostic counters.
- Native service symbols and Objective-C method signatures were checked against the new donor. The generated profile query has two additional optional arguments: country and viewer state. The request now uses a nil country and explicitly requests viewer state, preserving subscription-state fields that would otherwise be excluded. The new calling layout and optional argument representation are covered by the ABI fixtures and donor-contract checks.
- Exact image identities, native method and call relationships, writable monitor slots, and the runtime probe instructions are validated prior to package mutation. The native and original-startup modes both retain the original HBC.
- The metadata inspection tooling recognizes the donor's updated chained-fixup import format. The historical 32.0 inspection path remains available through the prior revision.

## Validation

`make test` passed all 174 Ubuntu tests, including host ABI and diagnostic coverage, actual 32.2 donor admission, profile/feed/content-label contracts, and in-memory assembly of runtime instrumentation in both launch modes. This includes a rejection test for a changed probe entry. Documentation and diff checks are required before submission.

Apple compilation, component verification and final packaging remain separate gates; they must succeed before creating a device IPA. The new donor has not yet been tested on an iPhone. A successful compile or package does not establish native startup, authorized session restoration, followed data, actual playback or zero runtime activity.

## Device acceptance

After assembly and local Feather signing, repeat the [native device checks](SWIFTUI_NATIVE_DEVICE_TEST.md), emphasizing:

- Cold startup, restored account and native logout/login ownership.
- Real follows, refresh, profile Home and About, follow/subscription state and notifications.
- Muted preview audio isolation, shared-player handoff, theatre playback and teardown, controls and quality preference.
- Chat reception and send, keyboard dismissal, background/foreground and reopening.
- Diagnostic counters remaining zero for RN/Hermes/worklet runtime creation in native mode, with positive observations on the original-startup control.

Retain the known working 32.0 build until these checks succeed. Do not infer device compatibility merely from donor admission.


## Apple validation attempt 1 and startup recovery

[Run 45809548028](https://github.com/BananaOnGitHub/Streamside/actions/runs/45809548028) compiled the native framework and coordinate-test fixture successfully. `testChatCatchUp` passed, exercising the composer, scroll-follow and keyboard behavior. The immediately following `testMarkedContentConsent` command wrote the result-bundle path and then stopped emitting progress. After 150 seconds, the startup deadline expired without a test suite or case start; the incomplete result bundle had no `Info.plist`. This was an infrastructure startup timeout, not an observed marked-content assertion failure. The exact cause within the hosted simulator is unconfirmed.

The runner now distinguishes startup from execution and result finalization. One recovery is allowed across the coordinate suite when the startup deadline expires with no observed XCTest suite or case output: reboot only the owned simulator, wait for readiness, and start that same mandatory gate with a different result-bundle path. Preserve the original timeout log. If recovery fails, any subsequent startup stall occurs, or XCTest has begun, the normal failure path remains in force. No test assertions, case selection, receipt requirements, individual case timeouts or outer workflow limits were changed.

All 178 Ubuntu tests passed, including the exact 32.2 donor checks. Local regression coverage checks successful startup recovery, failure when recovery stalls, rejection of recovery after execution evidence and the distinct execution-timeout classification. The next Apple run must pass all eight coordinate cases and existing component gates before IPA assembly. See the original [bounded CI evidence](https://github.com/BananaOnGitHub/Streamside/actions/runs/45809548028/artifacts/15113921491).


## Apple validation and local IPA candidate

[Run 45870999510](https://github.com/BananaOnGitHub/Streamside/actions/runs/45870999510) completed successfully against source `7538e89289f30f24c64d071bac99f991cc248aaa` using Xcode 26.6 (17F113), Swift 6.3.3 and iPhoneOS SDK 26.5. All eight coordinate cases passed, including marked-content consent. The simulator startup recovery was not needed in this run. The complete donor-free component archive and the Apple-compiled ABI were verified again on Ubuntu.

- Component archive SHA-256: `3fa1488134e0fe6454f13ffd3097c430ecfb4e8f660d64464d54fc35c06872a7`.
- Component manifest SHA-256: `ff555c8e6e6c116cde40b3493ce9e11b47b91e121d9aac5a4e9140fe658ade37`.
- Native proof ID: `41b5d24452d3be1e0bbb383571fc35dc35b27e356ee5cf810fa7d731ce0c6ba3`.

Local donor admission and assembly passed, validating 117 ABI entries, all 25 runtime probes, all retained donor entries and the unchanged original HBC. The native-only device candidate is `artifacts/native-frontend/twitch-32.2-7538e89/StreamsideNativeProof-Twitch32-native.ipa` (workspace-relative, outside the repository), 196,647,706 bytes, SHA-256 `4da9eb3a696a2bd88abe84b2b4eed8c9a20d514edab3ea9e5339ae5257e5c46e`. Its source and packaging revisions are both the successful Apple revision above. The full assembly manifest lives beside the IPA locally. No donor or IPA was uploaded to GitHub.

This candidate requires Feather signing and physical iPhone acceptance. Device behavior on Twitch 32.2, including real account, playback, chat and RN/Hermes/Worklets isolation, is not yet established. The previous 32.0 build remains available.
