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
